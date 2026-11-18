"""Bounded verification reports for trusted check callbacks.

Callbacks supply observations for the report and are expected to be read-only.
Use trusted callbacks and pass only public details and summary metrics. If a
callback raises, the report records its exception class and a fixed message.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


VerifierStatus = Literal["PASS", "WARNING", "FAIL"]
OverallStatus = Literal["PASS", "PASS_WITH_WARNINGS", "FAIL"]
MetricValue = str | int | float | bool | None
CHECK_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
METRIC_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class BackendVerificationError(ValueError):
    """Raised when the verifier registry itself is invalid."""


class VerificationObservation(BaseModel):
    """One verifier's sanitized result."""

    status: VerifierStatus
    detail: str = Field(min_length=1, max_length=400)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_metrics(self) -> "VerificationObservation":
        if len(self.metrics) > 16:
            raise ValueError("a verifier may expose at most 16 metrics")
        for key in self.metrics:
            if not METRIC_KEY_PATTERN.fullmatch(key):
                raise ValueError("verification metric keys must be normalized")
        return self


class VerificationCheck(BaseModel):
    """One completed backend check."""

    check_id: str = Field(min_length=3, max_length=80)
    category: Literal["DATABASE", "DATA", "POLICY", "PLATFORM", "WORKER"]
    label: str = Field(min_length=3, max_length=100)
    status: VerifierStatus
    detail: str = Field(min_length=1, max_length=400)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")


class BackendVerificationReport(BaseModel):
    """Deterministic result envelope for one read-only verification run."""

    report_id: Literal["offline-backend-verification-v1"]
    app_version: str = Field(min_length=1, max_length=40)
    environment: Literal["development"]
    generated_at: datetime
    overall_status: OverallStatus
    check_count: int = Field(gt=0, le=32)
    passed_count: int = Field(ge=0, le=32)
    warning_count: int = Field(ge=0, le=32)
    failed_count: int = Field(ge=0, le=32)
    database_writes: Literal[False] = False
    production_modified: Literal[False] = False
    checks: tuple[VerificationCheck, ...]
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_counts(self) -> "BackendVerificationReport":
        if self.check_count != len(self.checks):
            raise ValueError("verification check count drifted")
        if self.check_count != self.passed_count + self.warning_count + self.failed_count:
            raise ValueError("verification status counts drifted")
        return self


class VerificationSpec(BaseModel):
    """Metadata for one runtime verifier callback."""

    check_id: str = Field(min_length=3, max_length=80)
    category: Literal["DATABASE", "DATA", "POLICY", "PLATFORM", "WORKER"]
    label: str = Field(min_length=3, max_length=100)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_id(self) -> "VerificationSpec":
        if not CHECK_ID_PATTERN.fullmatch(self.check_id):
            raise ValueError("verification check IDs must be normalized")
        return self


VerifierCallback = Callable[[], VerificationObservation]


def observation(
    status: VerifierStatus,
    detail: str,
    **metrics: MetricValue,
) -> VerificationObservation:
    """Create a validated, non-sensitive verifier observation."""

    return VerificationObservation(status=status, detail=detail, metrics=metrics)


def _fingerprint(values: dict[str, object]) -> str:
    return sha256(
        json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def run_backend_verification(
    *,
    app_version: str,
    checks: Iterable[tuple[VerificationSpec, VerifierCallback]],
    now: Callable[[], datetime] | None = None,
) -> BackendVerificationReport:
    """Run a bounded verifier registry and fail closed on unexpected errors."""

    registry = tuple(checks)
    if not registry or len(registry) > 32:
        raise BackendVerificationError("the verifier registry size is invalid")
    check_ids = [spec.check_id for spec, _callback in registry]
    if len(check_ids) != len(set(check_ids)):
        raise BackendVerificationError("verification check IDs must be unique")

    completed: list[VerificationCheck] = []
    for spec, callback in registry:
        try:
            result = callback()
        except Exception as exc:  # sanitized fail-closed runtime boundary
            result = observation(
                "FAIL",
                "The verifier raised an unexpected bounded runtime error.",
                error_class=type(exc).__name__,
            )
        completed.append(
            VerificationCheck(
                **spec.model_dump(),
                status=result.status,
                detail=result.detail,
                metrics=result.metrics,
            )
        )

    passed = sum(item.status == "PASS" for item in completed)
    warnings = sum(item.status == "WARNING" for item in completed)
    failed = sum(item.status == "FAIL" for item in completed)
    overall: OverallStatus = (
        "FAIL" if failed else "PASS_WITH_WARNINGS" if warnings else "PASS"
    )
    generated_at = (now or (lambda: datetime.now(UTC)))().astimezone(UTC)
    if generated_at.tzinfo is None:
        raise BackendVerificationError("verification time must include a timezone")

    values: dict[str, object] = {
        "report_id": "offline-backend-verification-v1",
        "app_version": app_version,
        "environment": "development",
        "generated_at": generated_at.isoformat(),
        "overall_status": overall,
        "check_count": len(completed),
        "passed_count": passed,
        "warning_count": warnings,
        "failed_count": failed,
        "database_writes": False,
        "production_modified": False,
        "checks": [item.model_dump(mode="json") for item in completed],
    }
    return BackendVerificationReport(
        **values,
        result_sha256=_fingerprint(values),
    )
