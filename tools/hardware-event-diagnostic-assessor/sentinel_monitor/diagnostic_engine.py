from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .models import HardwareEvent, SystemSnapshot


@dataclass(slots=True, frozen=True)
class DiagnosticAssessment:
    status: str
    severity: str
    title: str
    likely_cause: str
    confidence: str
    evidence: tuple[str, ...]
    recommended_action: str
    verification: str
    automatic_action_taken: bool = False
    auto_cleared: bool = False


@dataclass(slots=True, frozen=True)
class _Fault:
    title: str
    likely_cause: str
    confidence: str
    severity: str
    evidence: tuple[str, ...]
    recommended_action: str
    automatic_action_taken: bool = False


class DiagnosticEngine:
    """Explain evidence and clear banners only after verified clean samples."""

    def __init__(
        self,
        *,
        auto_clear_samples: int = 5,
        session_started: datetime | None = None,
    ) -> None:
        self.auto_clear_samples = max(1, int(auto_clear_samples))
        self.session_started = session_started or datetime.now().astimezone()
        self._events: dict[tuple[str, int], HardwareEvent] = {}
        self._last_replays: dict[int, int] = {}
        self._fault: _Fault | None = None
        self._clean_samples = 0
        self._acknowledged = False
        self._last_assessment = self._normal_assessment()

    @property
    def assessment(self) -> DiagnosticAssessment:
        return self._last_assessment

    def acknowledge(self) -> DiagnosticAssessment:
        self._acknowledged = True
        self._last_assessment = replace(
            self._last_assessment,
            status="acknowledged",
            severity="normal",
            title=f"Acknowledged: {self._last_assessment.title}",
            verification=(
                "The banner is cleared manually. Evidence remains stored and "
                "any new event or replay increase will reactivate it."
            ),
        )
        return self._last_assessment

    def evaluate(self, snapshot: SystemSnapshot) -> DiagnosticAssessment:
        new_events = self._remember_events(snapshot.hardware_events)
        replay_increases = self._replay_increases(snapshot)
        source_problem = self._source_problem(snapshot)

        fault = self._classify_fault(
            snapshot,
            new_events=new_events,
            replay_increases=replay_increases,
            source_problem=source_problem,
        )
        if fault is not None:
            self._fault = fault
            self._clean_samples = 0
            self._acknowledged = False
            self._last_assessment = DiagnosticAssessment(
                status="active",
                severity=fault.severity,
                title=fault.title,
                likely_cause=fault.likely_cause,
                confidence=fault.confidence,
                evidence=fault.evidence,
                recommended_action=fault.recommended_action,
                verification="Waiting for consecutive clean diagnostic samples.",
                automatic_action_taken=fault.automatic_action_taken,
            )
            return self._last_assessment

        if self._acknowledged:
            return self._last_assessment

        self._clean_samples += 1
        verification = self._verification(snapshot)
        if self._fault is not None:
            self._last_assessment = self._recovery_assessment(
                self._fault,
                verification,
            )
            return self._last_assessment

        historical = self._historical_assessment(snapshot, verification)
        if historical is not None:
            self._last_assessment = historical
            return historical

        self._last_assessment = self._normal_assessment(verification)
        return self._last_assessment

    def _remember_events(
        self,
        events: list[HardwareEvent],
    ) -> list[HardwareEvent]:
        new_events: list[HardwareEvent] = []
        for event in events:
            key = (event.channel, event.record_id)
            if key not in self._events:
                self._events[key] = event
                new_events.append(event)
        return new_events

    def _replay_increases(
        self,
        snapshot: SystemSnapshot,
    ) -> list[tuple[int, int, int]]:
        increases: list[tuple[int, int, int]] = []
        for gpu in snapshot.gpus:
            current = gpu.pcie_replays_since_reset
            if current is None:
                continue
            previous = self._last_replays.get(gpu.index)
            if previous is not None and current > previous:
                increases.append((gpu.index, previous, current))
            self._last_replays[gpu.index] = current
        return increases

    @staticmethod
    def _source_problem(snapshot: SystemSnapshot) -> str | None:
        status = snapshot.source_status.get("Windows diagnostics", "")
        if status.startswith(("Read error", "Unavailable")):
            return status
        storage = snapshot.source_status.get("SQLite storage", "")
        if storage.startswith("Read error"):
            return storage
        if snapshot.gpus and any(
            gpu.pcie_replays_since_reset is None
            for gpu in snapshot.gpus
        ):
            return "NVIDIA PCIe replay counters unavailable; automatic retry active"
        return None

    def _classify_fault(
        self,
        snapshot: SystemSnapshot,
        *,
        new_events: list[HardwareEvent],
        replay_increases: list[tuple[int, int, int]],
        source_problem: str | None,
    ) -> _Fault | None:
        if replay_increases:
            evidence = tuple(
                f"GPU {index} PCIe replay counter increased {previous} -> {current}"
                for index, previous, current in replay_increases
            )
            return _Fault(
                title="Active PCIe replay increase detected",
                likely_cause=(
                    "PCIe link instability involving the indicated GPU, slot, "
                    "riser, power delivery, or motherboard path"
                ),
                confidence="High",
                severity="critical",
                evidence=evidence,
                recommended_action=(
                    "Do not reset the counter automatically. Preserve the evidence, "
                    "stop heavy GPU work safely, and inspect that physical PCIe path."
                ),
            )

        active_events = [
            event
            for event in new_events
            if event.timestamp >= self.session_started
        ]
        if active_events:
            event = max(active_events, key=lambda item: item.timestamp)
            return self._event_fault(event)

        if source_problem:
            return _Fault(
                title="Diagnostic source temporarily unavailable",
                likely_cause="A Sentinel collector or telemetry store failed a read/write check",
                confidence="High",
                severity="warning",
                evidence=(source_problem,),
                recommended_action=(
                    "Sentinel is retrying the internal operation automatically. "
                    "No driver, hardware, or Windows setting is being changed."
                ),
                automatic_action_taken=True,
            )
        return None

    @staticmethod
    def _event_fault(event: HardwareEvent) -> _Fault:
        evidence = (
            f"{event.timestamp:%Y-%m-%d %H:%M:%S} | "
            f"{event.provider} Event {event.event_id}",
            event.message or "No Windows event message was available",
        )
        if event.category == "WHEA PCIe":
            return _Fault(
                "New WHEA PCIe error detected",
                "Windows reported a corrected PCIe hardware/link error",
                "High",
                "critical",
                evidence,
                "Preserve the event and correlate its device path with the GPU bus/slot.",
            )
        if event.category == "WHEA Memory":
            return _Fault(
                "New WHEA memory error detected",
                "Windows reported a corrected system-memory hardware error",
                "High",
                "critical",
                evidence,
                (
                    "Preserve the event and correlate it with BIOS/BMC ECC records. "
                    "If it recurs, locate the affected DIMM and schedule an offline "
                    "memory test."
                ),
            )
        if event.category == "WHEA Corrected Hardware":
            return _Fault(
                "New corrected WHEA hardware error detected",
                "Windows reported a corrected processor, bus, or interconnect error",
                "High",
                "critical",
                evidence,
                (
                    "Preserve the event and correlate its processor APIC and error "
                    "type with BIOS/BMC, CPU, memory, PCIe-slot, and power-path "
                    "records before the next hardware change."
                ),
            )
        if event.category in {"NVIDIA driver", "Display reset"}:
            return _Fault(
                "New GPU driver event detected",
                "The NVIDIA/display driver reported a failure or recovery",
                "High",
                "critical",
                evidence,
                "Preserve the event; verify driver status and replay counters before changes.",
            )
        if event.category == "Bugcheck":
            return _Fault(
                "Windows bugcheck recorded",
                "Windows experienced a kernel crash",
                "High",
                "critical",
                evidence,
                "Preserve the dump and event data for stop-code analysis.",
            )
        if event.category in {"Unexpected restart", "Unexpected shutdown"}:
            return _Fault(
                "Unexpected restart recorded during monitoring",
                "Hard freeze, forced reset, power interruption, or kernel failure",
                "Low",
                "critical",
                evidence,
                "No automatic repair is safe without more evidence; continue correlation.",
            )
        if event.category == "Application crash":
            return _Fault(
                "Application crash recorded",
                "Windows recorded an application failure or hang",
                "Medium",
                "warning",
                evidence,
                "Preserve the event and correlate it with the affected program log.",
            )
        return _Fault(
            "New system diagnostic event detected",
            event.category,
            "Medium",
            event.severity,
            evidence,
            "Preserve the event and monitor for recurrence.",
        )

    def _recovery_assessment(
        self,
        fault: _Fault,
        verification: str,
    ) -> DiagnosticAssessment:
        if self._clean_samples >= self.auto_clear_samples:
            return DiagnosticAssessment(
                status="resolved",
                severity="normal",
                title=f"Recovered: {fault.title}",
                likely_cause=fault.likely_cause,
                confidence=fault.confidence,
                evidence=fault.evidence,
                recommended_action=(
                    "Automatic verification passed. The finding remains in history; "
                    "no risky system change was applied."
                ),
                verification=verification,
                automatic_action_taken=fault.automatic_action_taken,
                auto_cleared=True,
            )
        return DiagnosticAssessment(
            status="monitoring",
            severity="warning",
            title=f"Verifying recovery: {fault.title}",
            likely_cause=fault.likely_cause,
            confidence=fault.confidence,
            evidence=fault.evidence,
            recommended_action=fault.recommended_action,
            verification=(
                f"Clean verification sample {self._clean_samples}/"
                f"{self.auto_clear_samples}. {verification}"
            ),
            automatic_action_taken=fault.automatic_action_taken,
        )

    def _historical_assessment(
        self,
        snapshot: SystemSnapshot,
        verification: str,
    ) -> DiagnosticAssessment | None:
        historical = [
            event
            for event in self._events.values()
            if event.timestamp < self.session_started
        ]
        if not historical:
            nonzero = [
                gpu
                for gpu in snapshot.gpus
                if (gpu.pcie_replays_since_reset or 0) > 0
            ]
            if not nonzero:
                return None
            evidence = tuple(
                f"GPU {gpu.index} replay counter is {gpu.pcie_replays_since_reset}"
                for gpu in nonzero
            )
            title = "Historical non-zero PCIe replay counter"
            likely_cause = "A PCIe retry occurred earlier in the current boot"
            confidence = "Medium"
        else:
            latest = max(historical, key=lambda item: item.timestamp)
            display_time = (
                self._reported_shutdown_time(historical) or latest.timestamp
            )
            evidence = tuple(
                f"{event.timestamp:%Y-%m-%d %H:%M:%S} | "
                f"{event.provider} Event {event.event_id}"
                for event in sorted(historical, key=lambda item: item.timestamp)
            )
            categories = {event.category for event in historical}
            if categories <= {"Unexpected restart", "Unexpected shutdown"}:
                title = (
                    f"Historical unexpected restart recorded — "
                    f"{display_time:%b %d, %I:%M %p}"
                )
                likely_cause = (
                    "Windows confirms an unclean shutdown but cannot distinguish "
                    "a hard freeze, forced reset, or power interruption"
                )
                confidence = "Low"
            else:
                title = f"Historical diagnostic events retained — {latest.timestamp:%b %d}"
                likely_cause = ", ".join(sorted(categories))
                confidence = "Medium"

        if self._clean_samples >= self.auto_clear_samples:
            return DiagnosticAssessment(
                status="resolved",
                severity="normal",
                title=f"{title} | current checks clean",
                likely_cause=likely_cause,
                confidence=confidence,
                evidence=evidence,
                recommended_action=(
                    "No safe automatic system repair is justified. Evidence remains "
                    "stored for recurrence correlation."
                ),
                verification=verification,
                auto_cleared=True,
            )
        return DiagnosticAssessment(
            status="monitoring",
            severity="warning",
            title=title,
            likely_cause=likely_cause,
            confidence=confidence,
            evidence=evidence,
            recommended_action=(
                "Sentinel is checking current replay counters and diagnostic sources "
                "before clearing the main banner automatically."
            ),
            verification=(
                f"Clean verification sample {self._clean_samples}/"
                f"{self.auto_clear_samples}. {verification}"
            ),
        )

    @staticmethod
    def _reported_shutdown_time(
        events: list[HardwareEvent],
    ) -> datetime | None:
        marker = "previous system shutdown at "
        for event in events:
            message = event.message.lower()
            if marker not in message or " on " not in message:
                continue
            remainder = message.split(marker, 1)[1]
            time_text, date_and_suffix = remainder.split(" on ", 1)
            date_text = date_and_suffix.split(" was ", 1)[0]
            try:
                parsed = datetime.strptime(
                    f"{date_text.strip()} {time_text.strip()}",
                    "%m/%d/%Y %I:%M:%S %p",
                )
            except ValueError:
                continue
            return parsed.replace(tzinfo=event.timestamp.tzinfo)
        return None

    @staticmethod
    def _verification(snapshot: SystemSnapshot) -> str:
        replay_parts = [
            f"GPU {gpu.index} replay={gpu.pcie_replays_since_reset}"
            for gpu in snapshot.gpus
            if gpu.pcie_replays_since_reset is not None
        ]
        diagnostics = snapshot.source_status.get("Windows diagnostics", "unknown")
        return (
            f"{', '.join(replay_parts) or 'Replay counters unavailable'}; "
            f"Windows diagnostics: {diagnostics}"
        )

    @staticmethod
    def _normal_assessment(verification: str = "Waiting for the first sample") -> DiagnosticAssessment:
        return DiagnosticAssessment(
            status="normal",
            severity="normal",
            title="No active or historical hardware finding",
            likely_cause="None",
            confidence="High",
            evidence=(),
            recommended_action="Continue normal monitoring.",
            verification=verification,
        )
