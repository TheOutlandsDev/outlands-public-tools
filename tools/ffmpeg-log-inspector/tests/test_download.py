"""Stdlib CLI checks using only a copied inspector and fictional local logs.

Select PowerShell with OUTLANDS_PWSH. OUTLANDS_TEST_TEMP_ROOT can select an
existing ordinary local scratch parent. OUTLANDS_REQUIRE_SYMLINK_TEST=1 makes
native symbolic-link creation mandatory, including on Windows. Otherwise only
the native Windows privilege failure is skipped. Junction fixtures are Windows
only. No FFmpeg, media, device, network, module or installation is used.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
ENTRY = "Inspect-FFmpegLog.ps1"
INTERPRETATION = (
    "Observed supported text only. Counters, error phrases and progress=end do "
    "not prove recording success, media quality, elapsed wall time, device "
    "health or root cause. Other text and unsupported keys are not interpreted."
)
PROGRESS = b"frame=1\nout_time=00:00:00.125\nprogress=end\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def empty_stats() -> dict:
    return {
        "records": 0, "numericFields": 0, "frameObservations": 0,
        "timeObservations": 0, "unavailableFrames": 0, "unavailableTimes": 0,
        "lastFrame": None, "maximumFrame": None, "lastTimeSeconds": None,
        "maximumTimeSeconds": None, "frameDecreases": 0, "timeDecreases": 0,
    }


class DownloadCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        selected = os.environ.get("OUTLANDS_PWSH", "pwsh")
        cls.pwsh = shutil.which(selected)
        if cls.pwsh is None:
            raise RuntimeError("PowerShell 7.2+ is required; set OUTLANDS_PWSH")
        parent = os.environ.get("OUTLANDS_TEST_TEMP_ROOT")
        cls.scratch = tempfile.TemporaryDirectory(prefix="ffmpeg-download-", dir=parent)
        cls.root = Path(cls.scratch.name).resolve()
        cls.runtime = cls.root / "runtime"
        cls.runtime.mkdir()
        cls.entry = cls.runtime / ENTRY
        shutil.copyfile(SOURCE / ENTRY, cls.entry)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def setUp(self) -> None:
        self.work = self.root / self._testMethodName
        self.work.mkdir()
        self.sequence = 0

    def invoke(self, *arguments: str, entry: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
             str(entry or self.entry), *map(str, arguments)],
            cwd=self.runtime, capture_output=True, timeout=30, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    def fixture(self, data: bytes = PROGRESS, name: str | None = None) -> Path:
        self.sequence += 1
        path = self.work / (name or f"fixture-{self.sequence}.log")
        path.write_bytes(data)
        return path

    def inspect(self, path: Path | str, code: int = 0, *arguments: str) -> tuple[dict, bytes]:
        raw_path = str(path)
        path = Path(path)
        # The inspector rejects remote syntax before I/O; the test must too.
        remote_syntax = raw_path.startswith(("\\\\", "//"))
        before = path.read_bytes() if not remote_syntax and path.is_file() else None
        result = self.invoke("-LogPath", raw_path, *arguments)
        self.assertEqual(result.returncode, code, (result.stdout, result.stderr))
        self.assertEqual(result.stderr, b"")
        report = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["tool"], "ffmpeg-log-inspector")
        self.assertEqual(report["status"], {0: "observations", 1: "review", 2: "error"}[code])
        if before is not None:
            self.assertEqual(path.read_bytes(), before, "input bytes changed")
            if code != 2:
                self.assertEqual(report["input"], {"bytes": len(before), "sha256": digest(before)})
        if code == 2:
            self.assertEqual(set(report), {"schemaVersion", "tool", "status", "error", "coverage"})
            self.assertEqual(report["coverage"], "No complete report.")
        return report, result.stdout

    def error(self, path: Path | str, expected: str, *arguments: str) -> None:
        report, _ = self.inspect(path, 2, *arguments)
        self.assertEqual(report["error"], expected)

    def symlink(self, link: Path, target: Path, *, directory: bool = False) -> None:
        self.assertTrue(link.parent.resolve().is_relative_to(self.root))
        self.assertTrue(target.resolve().is_relative_to(self.root))
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            unavailable = isinstance(error, PermissionError) or getattr(error, "winerror", None) == 1314
            if os.name == "nt" and unavailable and os.environ.get("OUTLANDS_REQUIRE_SYMLINK_TEST") != "1":
                self.skipTest("Native symlink privilege unavailable")
            raise

    def junction(self, link: Path, target: Path) -> None:
        if os.name != "nt":
            self.skipTest("Native Windows junction fixture")
        self.assertTrue(link.parent.resolve().is_relative_to(self.root))
        self.assertTrue(target.resolve().is_relative_to(self.root))
        script = (
            "param([string]$Link,[string]$Target)\n"
            "$ErrorActionPreference='Stop'\n"
            "New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null\n"
        )
        helper = self.work / "make-junction.ps1"
        helper.write_text(script, encoding="utf-8")
        result = self.invoke(str(link), str(target), entry=helper)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertEqual(result.stderr, b"")
        self.assertTrue(link.is_junction(), "fixture must be a real Windows junction")

    def test_copied_runtime_and_help(self) -> None:
        self.assertEqual([p.name for p in self.runtime.iterdir()], [ENTRY])
        self.assertEqual(self.entry.read_bytes(), (SOURCE / ENTRY).read_bytes())
        result = self.invoke("-Help")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertIn(b"Usage:", result.stdout)
        self.assertIn(b"Neither 0 nor progress=end proves recording success.", result.stdout)
        self.assertEqual([p.name for p in self.runtime.iterdir()], [ENTRY])

    def test_authored_demo_modes_and_complete_report(self) -> None:
        demo = self.work / "demo"
        result = self.invoke("-Destination", str(demo), entry=SOURCE / "examples" / "Make-Demo.ps1")
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertEqual(result.stderr, b"")
        self.assertEqual(sorted(p.name for p in demo.iterdir()),
                         ["progress-demo.log", "review-demo.log", "stderr-demo.log"])
        for name, mode, code in (
            ("stderr-demo.log", "Stderr", 0),
            ("progress-demo.log", "Progress", 0),
            ("review-demo.log", "Progress", 1),
        ):
            for selected in ("Auto", mode):
                with self.subTest(name=name, mode=selected):
                    output = self.work / f"{name}-{selected}.json"
                    report, stdout = self.inspect(demo / name, code, "-Format", selected,
                                                  "-ReportPath", str(output))
                    self.assertEqual(report["requestedFormat"], selected)
                    report_bytes = output.read_bytes()
                    self.assertFalse(report_bytes.startswith(b"\xef\xbb\xbf"))
                    self.assertTrue(report_bytes.endswith(b"\n"))
                    self.assertFalse(report_bytes.endswith(b"\n\n"))
                    self.assertEqual(report_bytes, stdout.rstrip(b"\r\n") + b"\n")
                    self.assertEqual(json.loads(report_bytes), report)
                    if name == "stderr-demo.log":
                        self.assertEqual(report["stderrProgress"]["records"], 2)
                        self.assertEqual(report["stderrProgress"]["lastFrame"], 60)
                    elif name == "review-demo.log":
                        self.assertEqual(report["reviewReasons"],
                                         ["counter_decrease_observed", "recognized_error_phrase"])
                    else:
                        stats = empty_stats()
                        stats.update(records=2, numericFields=4, frameObservations=2,
                                     timeObservations=2, lastFrame=60, maximumFrame=60,
                                     lastTimeSeconds=2.0, maximumTimeSeconds=2.0)
                        expected = {
                            "schemaVersion": 1, "tool": "ffmpeg-log-inspector",
                            "status": "observations", "requestedFormat": selected,
                            "input": {"bytes": (demo / name).stat().st_size,
                                      "sha256": digest((demo / name).read_bytes())},
                            "coverage": {
                                "segments": 8, "nonemptySegments": 8, "ignoredSegments": 0,
                                "stderrCandidates": 0, "malformedStderrRecords": 0,
                                "structuredKeyValueSegments": 8, "ignoredStructuredKeys": 2,
                                "closedStructuredBlocks": 2, "invalidStructuredBlocks": 0,
                                "unterminatedStructuredBlock": False, "duplicateStructuredKeys": 0,
                                "continueMarkers": 1, "endMarkers": 1, "lastMarker": "end",
                            },
                            "stderrProgress": empty_stats(), "structuredProgress": stats,
                            "signalSegments": {key: 0 for key in (
                                "inputOutputError", "openError", "filterError", "deviceLost",
                                "conversionFailed", "decodeError")},
                            "reviewReasons": [], "interpretation": INTERPRETATION,
                        }
                        self.assertEqual(report, expected)
                        self.assertEqual(canonical_digest(json.loads(report_bytes)), canonical_digest(expected))
                    saved_hash = digest(report_bytes)
                    self.error(demo / name, "input_or_output_error", "-ReportPath", str(output))
                    self.assertEqual(digest(output.read_bytes()), saved_hash)

    def test_utf8_bom_and_separator_forms(self) -> None:
        for separator, bom, trailing in ((b"\n", b"", True), (b"\n", b"\xef\xbb\xbf", True),
                                         (b"\r", b"", True), (b"\r\n", b"", True),
                                         (b"\n", b"", False)):
            with self.subTest(separator=separator, bom=bool(bom), trailing=trailing):
                data = bom + separator.join(PROGRESS.rstrip(b"\n").split(b"\n"))
                if trailing:
                    data += separator
                report, _ = self.inspect(self.fixture(data))
                self.assertEqual(report["coverage"]["segments"], 3)
                self.assertEqual(report["structuredProgress"]["lastTimeSeconds"], 0.125)
        self.error(self.fixture(b"\xef\xbb\xbf\xef\xbb\xbf" + PROGRESS), "unsupported_control_character")

    def test_strict_utf8_and_controls(self) -> None:
        for data in (b"\xff\xfe", b"\xc0\xaf", b"\xe2\x82"):
            with self.subTest(invalid_utf8=data):
                self.error(self.fixture(data), "input_or_output_error")
        for control in ("\0", "\x1b", "\x7f", "\x85", "\u202e"):
            with self.subTest(control=repr(control)):
                self.error(self.fixture(PROGRESS + control.encode()), "unsupported_control_character")

    def test_incomplete_and_ambiguous_blocks(self) -> None:
        cases = (
            (b"frame=1\nout_time=00:00:00.1", "unterminated_structured_block", 0),
            (b"frame=1\nprogress=continue\n", "no_final_end_marker", 1),
            (b"frame=1\nframe=2\nprogress=end\n", "invalid_structured_blocks", 0),
            (b"label=a\nlabel=b\nframe=1\nprogress=end\n", "invalid_structured_blocks", 0),
            (b"frame=1\nFictional interrupted line\nprogress=end\n", "invalid_structured_blocks", 0),
            (b"frame=1\nprogress=done\n", "invalid_structured_blocks", 0),
        )
        for data, reason, records in cases:
            with self.subTest(data=data):
                report, _ = self.inspect(self.fixture(data), 1, "-Format", "Progress")
                self.assertIn(reason, report["reviewReasons"])
                self.assertEqual(report["structuredProgress"]["records"], records)

    def test_malformed_numeric_fields_are_discarded(self) -> None:
        cases = (
            ("x", "00:00:01"), ("-1", "00:00:01"), ("1e3", "00:00:01"),
            ("9999999999999999999999", "00:00:01"), ("1", "00:60:00"),
            ("1", "-00:00:01"), ("1", "00:00:01,5"), ("1", "NaN"),
            ("1", "00:00:01.1234567"), ("1", "999999:59:59"),
        )
        for frame, clock in cases:
            for mode in ("Stderr", "Progress"):
                with self.subTest(frame=frame, clock=clock, mode=mode):
                    text = (f"frame={frame} time={clock}\n" if mode == "Stderr" else
                            f"frame={frame}\nout_time={clock}\nprogress=end\n")
                    report, _ = self.inspect(self.fixture(text.encode()), 1, "-Format", mode)
                    summary = "stderrProgress" if mode == "Stderr" else "structuredProgress"
                    self.assertEqual(report[summary]["records"], 0)
                    self.assertEqual(report[summary]["numericFields"], 0)
                    self.assertIn("malformed_stderr_records" if mode == "Stderr" else
                                  "invalid_structured_blocks", report["reviewReasons"])

    def test_zero_unavailable_and_audio_observations(self) -> None:
        cases = (
            (b"frame=0\nout_time=00:00:00\nprogress=end\n", 0, 0, 0),
            (b"frame=N/A\nout_time=N/A\nprogress=end\n", 1, None, None),
            (b"out_time=00:00:03.25\nprogress=end\n", 0, None, 3.25),
            (b"frame=7\nout_time=00:00:00.5\nprogress=continue\nframe=N/A\nout_time=N/A\nprogress=end\n",
             0, 7, 0.5),
        )
        for data, code, frame, clock in cases:
            with self.subTest(data=data):
                report, _ = self.inspect(self.fixture(data), code)
                stats = report["structuredProgress"]
                self.assertEqual(stats["lastFrame"], frame)
                self.assertEqual(stats["lastTimeSeconds"], clock)
                if b"N/A" in data:
                    self.assertEqual(stats["unavailableFrames"], 1)
                    self.assertEqual(stats["unavailableTimes"], 1)

    def test_mixed_decreasing_and_multiple_end_observations(self) -> None:
        mixed, _ = self.inspect(self.fixture(b"frame=5 time=00:00:05\n" + PROGRESS), 1)
        self.assertIn("mixed_progress_formats", mixed["reviewReasons"])
        self.assertEqual(mixed["stderrProgress"]["lastFrame"], 5)
        self.assertEqual(mixed["structuredProgress"]["lastFrame"], 1)
        decrease, _ = self.inspect(self.fixture(
            b"frame=10\nout_time=00:00:02\nprogress=continue\nframe=2\nout_time=00:00:01\nprogress=end\n"), 1)
        self.assertIn("counter_decrease_observed", decrease["reviewReasons"])
        self.assertEqual(decrease["structuredProgress"]["maximumFrame"], 10)
        self.assertEqual(decrease["structuredProgress"]["lastFrame"], 2)
        self.assertEqual(decrease["structuredProgress"]["frameDecreases"], 1)
        self.assertEqual(decrease["structuredProgress"]["timeDecreases"], 1)
        multiple, _ = self.inspect(self.fixture(b"frame=1\nprogress=end\nframe=2\nprogress=end\n"), 1)
        self.assertIn("multiple_end_markers", multiple["reviewReasons"])
        self.assertEqual(multiple["coverage"]["endMarkers"], 2)

    def test_empty_and_ignored_text_requires_review(self) -> None:
        for data, ignored in ((b"", 0), (b"Fictional banner only\n", 1),
                              (b"[application] frame=1 time=00:00:01\n", 1)):
            with self.subTest(data=data):
                report, _ = self.inspect(self.fixture(data), 1)
                self.assertEqual(report["coverage"]["ignoredSegments"], ignored)
                self.assertEqual(report["reviewReasons"], ["no_supported_numeric_progress"])

    def test_numeric_ceiling_boundaries(self) -> None:
        for frame, clock, code in (("1000000000000", "277777:46:40", 0),
                                    ("1000000000001", "00:00:00", 1),
                                    ("0", "277777:46:40.000001", 1)):
            with self.subTest(frame=frame, clock=clock):
                report, _ = self.inspect(self.fixture(
                    f"frame={frame}\nout_time={clock}\nprogress=end\n".encode()), code)
                if code == 0:
                    self.assertEqual(report["structuredProgress"]["lastFrame"], 1_000_000_000_000)
                    self.assertEqual(report["structuredProgress"]["lastTimeSeconds"], 1_000_000_000)
                else:
                    self.assertEqual(report["structuredProgress"]["records"], 0)

    def test_segment_character_boundaries(self) -> None:
        report, _ = self.inspect(self.fixture(b"x" * 16_384 + b"\n" + PROGRESS))
        self.assertEqual(report["coverage"]["ignoredSegments"], 1)
        self.error(self.fixture(b"x" * 16_385), "segment_character_limit")

    def test_segment_count_boundaries(self) -> None:
        report, _ = self.inspect(self.fixture(b"\n" * 99_999 + b"frame=1 time=00:00:01\n"))
        self.assertEqual(report["coverage"]["segments"], 100_000)
        self.error(self.fixture(b"\n" * 100_001), "segment_count_limit")

    def test_input_byte_boundaries(self) -> None:
        path = self.fixture((b"x" * 16_383 + b"\n") * 1024)
        self.assertEqual(path.stat().st_size, 16_777_216)
        report, _ = self.inspect(path, 1)
        self.assertEqual(report["coverage"]["segments"], 1024)
        with path.open("ab") as stream:
            stream.write(b"x")
        self.error(path, "log_byte_limit")

    def test_structured_key_boundaries(self) -> None:
        for unknown, code in ((126, 0), (127, 2)):
            with self.subTest(distinct_keys=unknown + 2):
                data = "".join(f"key{i}=fictional\n" for i in range(unknown)).encode() + b"frame=1\nprogress=end\n"
                path = self.fixture(data)
                if code == 2:
                    self.error(path, "structured_key_limit")
                else:
                    report, _ = self.inspect(path)
                    self.assertEqual(report["coverage"]["ignoredStructuredKeys"], 126)

    def test_raw_markers_paths_and_signal_text_are_redacted(self) -> None:
        marker = "FICTIONAL_PRIVATE_MARKER"
        source = self.fixture((
            f"private_key_{marker}=/fictional/{marker}/recording.mov\n"
            "frame=1\nout_time=00:00:00.125\nprogress=end\n"
            f"Input/output error: /fictional/{marker}/input.mov\n"
            f"Error opening {marker}\nCould not run filter {marker}\n"
            f"Device {marker} was lost\nConversion failed! {marker}\n"
            f"Error while decoding {marker}\n"
        ).encode(), f"{marker}.log")
        output = self.work / f"{marker}-report.json"
        report, stdout = self.inspect(source, 1, "-ReportPath", str(output))
        self.assertEqual(report["signalSegments"], {key: 1 for key in (
            "inputOutputError", "openError", "filterError", "deviceLost", "conversionFailed", "decodeError")})
        for private in (marker, str(source), str(output), "/fictional/", "recording.mov", "private_key_"):
            self.assertNotIn(private.encode(), stdout)
            self.assertNotIn(private.encode(), output.read_bytes())
        missing = self.work / f"{marker}-absent.log"
        _, failure = self.inspect(missing, 2)
        self.assertNotIn(marker.encode(), failure)
        self.assertNotIn(str(self.work).encode(), failure)

    def test_input_output_and_existing_report_are_preserved(self) -> None:
        source = self.fixture()
        existing = self.work / "existing.json"
        sentinel = b"FICTIONAL_EXISTING_REPORT\r\n"
        existing.write_bytes(sentinel)
        self.error(source, "input_or_output_error", "-ReportPath", str(existing))
        self.assertEqual(existing.read_bytes(), sentinel)
        self.error(source, "input_or_output_error", "-ReportPath", str(source))
        self.assertEqual(source.read_bytes(), PROGRESS)
        missing_parent = self.work / "absent"
        self.error(source, "existing_parent_required", "-ReportPath", str(missing_parent / "report.json"))
        self.assertFalse(missing_parent.exists())

    def test_paths_and_format_are_validated(self) -> None:
        source = self.fixture()
        for path, expected in (
            (Path("relative.log"), "absolute_local_path_required"),
            (self.work / "absent.log", "regular_input_required"),
            (self.work, "regular_input_required"),
            (str(self.work) + os.sep + "." + os.sep + source.name, "canonical_local_path_required"),
            ("//fictional-invalid-host/share/log.txt", "absolute_local_path_required"),
            (str(self.work / "control") + "\u202e.log", "control_in_path"),
        ):
            with self.subTest(path=str(path)):
                self.error(path, expected)
        self.error(source, "format_invalid", "-Format", "progress")

    def test_symbolic_link_input_is_refused(self) -> None:
        target = self.fixture()
        link = self.work / "linked.log"
        self.symlink(link, target)
        self.assertTrue(link.is_symlink())
        self.error(link, "linked_path_rejected")

    def test_symbolic_link_input_parent_is_refused(self) -> None:
        target = self.work / "target"
        target.mkdir()
        source = target / "input.log"
        source.write_bytes(PROGRESS)
        link = self.work / "linked-parent"
        self.symlink(link, target, directory=True)
        self.assertTrue(link.is_symlink())
        self.error(link / source.name, "linked_path_rejected")

    def test_symbolic_link_output_parent_is_refused(self) -> None:
        source = self.fixture()
        target = self.work / "target"
        target.mkdir()
        sentinel = target / "existing.txt"
        sentinel.write_bytes(b"FICTIONAL_UNCHANGED")
        link = self.work / "linked-parent"
        self.symlink(link, target, directory=True)
        self.assertTrue(link.is_symlink())
        self.error(source, "linked_path_rejected", "-ReportPath", str(link / "report.json"))
        self.assertEqual(sorted(p.name for p in target.iterdir()), [sentinel.name])
        self.assertEqual(sentinel.read_bytes(), b"FICTIONAL_UNCHANGED")

    def test_windows_junction_input_parent_is_refused(self) -> None:
        target = self.work / "target"
        target.mkdir()
        source = target / "input.log"
        source.write_bytes(PROGRESS)
        link = self.work / "junction-parent"
        self.junction(link, target)
        self.error(link / source.name, "linked_path_rejected")

    def test_windows_junction_output_parent_is_refused(self) -> None:
        source = self.fixture()
        target = self.work / "target"
        target.mkdir()
        sentinel = target / "existing.txt"
        sentinel.write_bytes(b"FICTIONAL_UNCHANGED")
        link = self.work / "junction-parent"
        self.junction(link, target)
        self.error(source, "linked_path_rejected", "-ReportPath", str(link / "report.json"))
        self.assertEqual(sorted(p.name for p in target.iterdir()), [sentinel.name])
        self.assertEqual(sentinel.read_bytes(), b"FICTIONAL_UNCHANGED")


if __name__ == "__main__":
    unittest.main()
