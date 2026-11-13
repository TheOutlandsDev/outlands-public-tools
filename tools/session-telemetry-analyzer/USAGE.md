# Fictional saved-session telemetry walkthrough

This driver reads invented saved JSONL only. It never launches a game, monitors
a process, collects live telemetry or verifies capture completeness. Each file
is a separate observation set. Repeated rows and distinct identical files remain
repeated observations; no pooling, deduplication, session segmentation or unique
entity inference is performed. Statistics do not establish causes, rates,
probabilities, game correctness or runtime performance.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment and external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands use
`-E -s -B` so sibling support imports work while environment/user site settings
and bytecode writes are disabled. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_telemetry_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with an owned directory;
do not choose links/reparse routes, network paths or real capture collections.
The script creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_telemetry_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_telemetry_walkthrough.py" "$module" "$privateParent"
```

The clean fixture has three snapshots but two valid samples for each population:
players `6/2`, bots `12/2`, tracked active `4/2`. The missing-fields fixture has
one valid zero player sample, mean `0/1`; bot/tracking means remain null. The
ratios are exact numerator/denominator objects, not rounded numbers. Null,
booleans and decimal population declarations are invalid, never zero samples.
Line-of-sight denominators count only actual booleans, with missing/invalid
entries and collections counted separately.

Time is an exact declared decimal, not a measured clock or inferred duration.
The guide detects a decrease beyond binary-float precision and checks that an
invalid last value does not overwrite the previous valid declaration. Duplicate
JSON keys have no arbitrary winner. Multiple end rows hold dropped-line values
even when equal or only one is valid. A single positive declaration is reported
as declared dropped data, not independently measured loss.

Coverage remains visible for malformed rows, BOM/blank extensions, unsupported
types/fields and ambiguous markers. Valid selected observations still contribute.
There is no details mode; raw records, unknown values, map names and filenames
stay omitted. Hashes, sizes, counts, declared times and structure can identify
material, so omission is not anonymization.

The driver checks exact JSON report fields, fixed stdout bytes and empty stderr,
independently recomputes source lengths/SHA-256 and both report payload hashes,
and verifies unchanged input/runtime bytes, exact created files and no bytecode.
Unsigned manifests prove consistency only, not origin, authenticity or capture
completeness. Eight controlled refusals cover paths, outputs, unsupported details
and physical-line, decimal-exponent and nonblank-record bounds. Review/incomplete
exits are checked internally; the complete driver exits 0 only if all checks pass.

## Executable driver

```python
"""Summarize only fictional saved JSONL; never collect live telemetry."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

if not __debug__:
    raise RuntimeError("ASSERTIONS_REQUIRED")
module = Path(sys.argv[1]).resolve(strict=True)
parent = Path(sys.argv[2]).resolve(strict=True)
assert module.is_absolute() and parent.is_absolute() and parent.is_dir()
assert not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not module.is_symlink() and not parent.is_symlink()
assert not getattr(parent, "is_junction", lambda: False)()
work = Path(tempfile.mkdtemp(prefix="fictional-saved-telemetry-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("telemetry_analyzer.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout, wire=None):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    expected_wire = json.dumps(expected_stdout, sort_keys=True) if wire is None else wire
    assert result.stdout == (expected_wire+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-saved-jsonl", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 3},
        json.dumps({"status": "FICTIONAL_EXAMPLES_CREATED", "files": 3}))
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.jsonl", "review.jsonl", "missing-fields.jsonl"}
crafted = work/"crafted"; crafted.mkdir()
def row(kind, **payload):
    return {"type": kind, "payload": payload}
def encode(rows):
    return ("\n".join(json.dumps(value, separators=(",", ":")) for value in rows)+"\n").encode()
values = {
    "null-counts.jsonl": encode([row("snapshot", player_count=0, bot_count=None, tracking={"active_count": None}, line_of_sight=[]),
                                row("snapshot", player_count=None, bot_count=2.0, tracking=None, line_of_sight=None), row("snapshot")]),
    "decimal-time.jsonl": b'{"type":"snapshot","payload":{"raid_seconds":0.1000000000000000000000000001}}\n'
                          b'{"type":"snapshot","payload":{"raid_seconds":0.1000000000000000000000000000}}\n'
                          b'{"type":"snapshot","payload":{"raid_seconds":null}}\n',
    "duplicate-key.jsonl": b'{"type":"snapshot","payload":{"player_count":1,"player_count":7}}\n'+encode([row("snapshot", player_count=2)]),
    "positive-drop.jsonl": encode([row("raid_end", dropped_lines=3)]),
    "one-valid-end.jsonl": encode([row("raid_end", dropped_lines=3), row("raid_end")]),
    "los.jsonl": encode([row("snapshot", line_of_sight=[{"main_can_see_bot": True}, {"main_can_see_bot": False}, {},
                         {"main_can_see_bot": 1}, None, {"private_id": "FICTIONAL_PRIVATE_MARKER"}])]),
    "coverage.jsonl": b'\xef\xbb\xbf'+encode([row("raid_start", map="</pre><script>fiction</script>")])+b'\n'+encode([
        row("private.producer"), {}, {"type": "snapshot", "payload": {"player_count": 1, "extra": "FICTIONAL_PRIVATE_MARKER"}, "private_id": "FICTIONAL_PRIVATE_MARKER"}]),
    "clean-copy.jsonl": (fixtures/"clean.jsonl").read_bytes(),
    "repeated.jsonl": encode([row("raid_start"), row("raid_start"), row("snapshot", player_count=2, bot_count=3), row("snapshot", player_count=2, bot_count=3)]),
    "long-line.jsonl": b"X"*8193,
    "number-bound.jsonl": b'{"type":"snapshot","payload":{"raid_seconds":1e1001}}\n',
    "record-bound.jsonl": encode([row("snapshot")])*4001,
}
for name, data in values.items():
    (crafted/name).write_bytes(data)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 15
reports = []; source_hashes_checked = 0

def population(samples=0, missing=0, invalid=0, total=0, maximum=None):
    return {"samples": samples, "missing_samples": missing, "invalid_samples": invalid,
            "sum": str(total), "maximum": maximum,
            "sample_mean": {"numerator": str(total), "denominator": samples} if samples else None}
def capture(lines, nonblank, decoded, accepted, events):
    counts = {name: events.get(name, 0) for name in ("raid_start", "snapshot", "tracking_assigned", "raid_end")}
    return {"source": "input-0001", "physical_lines": lines, "blank_rows": lines-nonblank,
            "nonblank_rows": nonblank, "decoded_rows": decoded, "accepted_events": accepted,
            "malformed_json_rows": nonblank-decoded, "invalid_envelope_rows": 0, "unsupported_event_rows": 0,
            "event_counts": counts,
            "populations": {name: population(missing=counts["snapshot"]) for name in ("players", "bots", "tracked_active")},
            "line_of_sight": {"present_collections": 0, "missing_collections": counts["snapshot"], "invalid_collections": 0,
                "declared_entries": 0, "valid_boolean_samples": 0, "visible_samples": 0,
                "missing_entry_values": 0, "invalid_entry_values": 0, "visible_fraction": None},
            "declared_time": {"valid_declarations": 0, "invalid_declarations": 0, "last_in_file_seconds": None},
            "dropped_data": {"end_rows": counts["raid_end"], "valid_declarations": 0, "invalid_declarations": 0,
                             "state": "unspecified", "declared_dropped_lines": None}}

def inspect_case(case, selected, report_name, expected_exit, captures, findings=(), coverage=()):
    global source_hashes_checked
    output = work/report_name
    args = [value for path in selected for value in ("--file", path)]+["--output", output]
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "selected_files": len(selected), "nonblank_records_observed": sum(row["nonblank_rows"] for row in captures),
                "findings": len(findings), "coverage_issues": len(coverage)}
    command(case, "telemetry_analyzer.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert set(report) == {"schema_version", "tool", "scope", "sources", "captures", "findings", "coverage_issues",
                           "selected_files", "nonblank_records_observed", "status"}
    assert report["schema_version"] == 1 and report["tool"] == "Offline Session Telemetry Analyzer"
    assert report["scope"] == "Selected saved JSONL subset; per-file observations, not distinct-session or runtime evidence."
    assert report["status"] == expected["status"] and report["selected_files"] == len(selected)
    assert report["nonblank_records_observed"] == expected["nonblank_records_observed"]
    expected_sources = []; expected_captures = []
    for index, (path, expected_capture) in enumerate(zip(selected, captures, strict=True), 1):
        data = path.read_bytes(); token = f"input-{index:04d}"
        expected_sources.append({"id": token, "bytes": len(data), "sha256": digest(data)})
        record = copy.deepcopy(expected_capture); record["source"] = token; expected_captures.append(record)
        source_hashes_checked += 1
    assert report["sources"] == expected_sources and report["captures"] == expected_captures
    def issues(values):
        rows = []
        for value in values:
            code, source, line, *field = value
            record = {"code": code, "source": f"input-{source:04d}", "line": line}
            if field: record["field"] = field[0]
            rows.append(record)
        return rows
    assert report["findings"] == issues(findings) and report["coverage_issues"] == issues(coverage)
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    assert all(marker not in data for data in payloads.values() for marker in
               (b"FictionalOrchard", b"FICTIONAL_PRIVATE_MARKER", b"private.producer", b"<script>", str(work).encode(), str(module).encode()))
    reports.append(report_name)
    return report

clean = capture(6, 6, 6, 6, {"raid_start": 1, "snapshot": 3, "tracking_assigned": 1, "raid_end": 1})
clean["populations"] = {"players": population(2, 1, 0, 6, 4), "bots": population(2, 1, 0, 12, 8), "tracked_active": population(2, 1, 0, 4, 3)}
clean["line_of_sight"].update(present_collections=2, missing_collections=1, declared_entries=2, valid_boolean_samples=2,
                               visible_samples=1, visible_fraction={"numerator": "1", "denominator": 2})
clean["declared_time"].update(valid_declarations=4, last_in_file_seconds="1.0")
clean["dropped_data"].update(valid_declarations=1, state="declared", declared_dropped_lines="0")
clean_report = inspect_case("clean-per-metric-denominators", [fixtures/"clean.jsonl"], "clean-report", 0, [clean])
missing = capture(2, 2, 2, 2, {"snapshot": 2}); missing["populations"]["players"] = population(1, 1, 0, 0, 0)
inspect_case("zero-is-valid-missing-means-null", [fixtures/"missing-fields.jsonl"], "missing-report", 0, [missing])
review = capture(4, 4, 3, 3, {"snapshot": 1, "raid_end": 2})
review["populations"] = {"players": population(invalid=1), "bots": population(1, 0, 0, 3, 3), "tracked_active": population(invalid=1)}
review["dropped_data"].update(valid_declarations=2, state="ambiguous_multiple_end_rows")
inspect_case("malformed-record-and-equal-end-values-held", [fixtures/"review.jsonl"], "review-report", 1, [review], coverage=[
    ("POPULATION_VALUE_INVALID", 1, 1, "players"), ("POPULATION_CONTAINER_INVALID", 1, 1, "tracked_active"),
    ("INVALID_JSON", 1, 4), ("MULTIPLE_END_MARKERS", 1, 0)])
nulls = capture(3, 3, 3, 3, {"snapshot": 3})
nulls["populations"] = {"players": population(1, 1, 1, 0, 0), "bots": population(0, 1, 2), "tracked_active": population(0, 1, 2)}
nulls["line_of_sight"].update(present_collections=1, missing_collections=1, invalid_collections=1)
inspect_case("null-and-decimal-counts-never-become-zero", [crafted/"null-counts.jsonl"], "null-report", 1, [nulls], coverage=[
    ("POPULATION_VALUE_INVALID", 1, 1, "bots"), ("POPULATION_VALUE_INVALID", 1, 1, "tracked_active"),
    ("POPULATION_VALUE_INVALID", 1, 2, "players"), ("POPULATION_VALUE_INVALID", 1, 2, "bots"),
    ("POPULATION_CONTAINER_INVALID", 1, 2, "tracked_active"), ("LOS_COLLECTION_INVALID", 1, 2)])
decimal = capture(3, 3, 3, 3, {"snapshot": 3})
decimal["declared_time"].update(valid_declarations=2, invalid_declarations=1, last_in_file_seconds="0.1000000000000000000000000000")
inspect_case("exact-decimal-time-decrease-and-invalid-last-value", [crafted/"decimal-time.jsonl"], "decimal-report", 1, [decimal],
             findings=[("DECLARED_TIME_DECREASE", 1, 2)], coverage=[("DECLARED_SECONDS_INVALID", 1, 3)])
duplicate = capture(2, 2, 1, 1, {"snapshot": 1}); duplicate["populations"]["players"] = population(1, 0, 0, 2, 2)
inspect_case("duplicate-json-key-has-no-value-winner", [crafted/"duplicate-key.jsonl"], "duplicate-key-report", 1, [duplicate],
             coverage=[("DUPLICATE_JSON_KEY", 1, 1)])
positive = capture(1, 1, 1, 1, {"raid_end": 1}); positive["dropped_data"].update(valid_declarations=1, state="declared", declared_dropped_lines="3")
inspect_case("single-positive-drop-is-declared-not-measured", [crafted/"positive-drop.jsonl"], "positive-drop-report", 1, [positive],
             findings=[("DECLARED_DROPPED_LINES", 1, 0)])
ambiguous = capture(2, 2, 2, 2, {"raid_end": 2}); ambiguous["dropped_data"].update(valid_declarations=1, state="ambiguous_multiple_end_rows")
inspect_case("multiple-ends-with-one-valid-drop-still-ambiguous", [crafted/"one-valid-end.jsonl"], "ambiguous-drop-report", 1, [ambiguous],
             coverage=[("MULTIPLE_END_MARKERS", 1, 0)])
los = capture(1, 1, 1, 1, {"snapshot": 1})
los["line_of_sight"].update(present_collections=1, missing_collections=0, declared_entries=6, valid_boolean_samples=2,
                           visible_samples=1, missing_entry_values=2, invalid_entry_values=2,
                           visible_fraction={"numerator": "1", "denominator": 2})
inspect_case("line-of-sight-denominator-uses-only-booleans", [crafted/"los.jsonl"], "los-report", 1, [los], coverage=[
    ("LOS_VALUE_INVALID", 1, 1), ("LOS_ENTRY_INVALID", 1, 1), ("LOS_FIELDS_UNSUPPORTED", 1, 1)])
coverage_capture = capture(5, 4, 4, 2, {"raid_start": 1, "snapshot": 1})
coverage_capture.update(invalid_envelope_rows=1, unsupported_event_rows=1)
coverage_capture["populations"]["players"] = population(1, 0, 0, 1, 1)
inspect_case("bom-blank-unknown-fields-and-private-values", [crafted/"coverage.jsonl"], "coverage-report", 1, [coverage_capture], coverage=[
    ("UTF8_BOM_EXTENSION", 1, 1), ("BLANK_RECORD_LINE", 1, 2), ("EVENT_TYPE_UNSUPPORTED", 1, 3),
    ("EVENT_ENVELOPE_INVALID", 1, 4), ("ENVELOPE_FIELDS_UNSUPPORTED", 1, 5), ("PAYLOAD_FIELDS_UNSUPPORTED", 1, 5)])
separate = inspect_case("selected-files-stay-separate-without-pooling", [fixtures/"clean.jsonl", fixtures/"missing-fields.jsonl"],
                        "separate-report", 0, [clean, missing])
assert separate["captures"][0] == clean_report["captures"][0]
copied = inspect_case("identical-distinct-files-are-repeated-observations", [fixtures/"clean.jsonl", crafted/"clean-copy.jsonl"],
                      "copied-file-report", 0, [clean, clean])
assert copied["sources"][0]["sha256"] == copied["sources"][1]["sha256"] and copied["selected_files"] == 2
repeated = capture(4, 4, 4, 4, {"raid_start": 2, "snapshot": 2})
repeated["populations"]["players"] = population(2, 0, 0, 4, 2)
repeated["populations"]["bots"] = population(2, 0, 0, 6, 3)
inspect_case("repeated-rows-contribute-without-unique-entity-inference", [crafted/"repeated.jsonl"], "repeated-row-report", 1, [repeated],
             coverage=[("MULTIPLE_START_MARKERS", 1, 0)])

def refusal(case, selected, code, output=None, extra=()):
    args = [value for path in selected for value in ("--file", path)]+["--output", output or work/(case+"-output"), *extra]
    command(case, "telemetry_analyzer.py", args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-same-file-alias", [fixtures/"clean.jsonl", fixtures/"clean.jsonl"], "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", [fixtures/"clean.jsonl"], "OUTPUT_EXISTS", output=work/"clean-report")
command("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], 2,
        {"status": "INCOMPLETE", "error": "OUTPUT_EXISTS"})
refusal("refuse-relative-input", ["relative.jsonl"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-unsupported-details-mode", [fixtures/"clean.jsonl"], "ARGUMENTS_INVALID", extra=["--include-details"])
refusal("refuse-physical-line-bound", [crafted/"long-line.jsonl"], "TEXT_LINE_LIMIT")
refusal("refuse-decimal-exponent-bound", [crafted/"number-bound.jsonl"], "JSON_NUMBER_LIMIT")
refusal("refuse-nonblank-record-bound", [crafted/"record-bound.jsonl"], "TELEMETRY_RECORD_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 13 and len(expected_files) == 54 and source_hashes_checked == 15
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 13, "payload_hashes_verified": 26,
                  "saved_source_hashes_checked": 15, "fixture_files_preserved": 15,
                  "expected_workspace_files": 54, "unexpected_application_files": 0,
                  "per_metric_denominators_checked": True, "per_file_isolation_checked": True,
                  "ambiguous_drops_held": True, "exact_decimal_time_checked": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "live_collection_performed": False, "games_launched": False, "processes_monitored": False,
                  "real_user_captures_used": False, "capture_completeness_verified": False,
                  "unique_entities_inferred": False, "causal_diagnosis_performed": False,
                  "runtime_performance_verified": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-saved-jsonl",
    "exit_code": 0
  },
  {
    "case": "clean-per-metric-denominators",
    "exit_code": 0
  },
  {
    "case": "zero-is-valid-missing-means-null",
    "exit_code": 0
  },
  {
    "case": "malformed-record-and-equal-end-values-held",
    "exit_code": 1
  },
  {
    "case": "null-and-decimal-counts-never-become-zero",
    "exit_code": 1
  },
  {
    "case": "exact-decimal-time-decrease-and-invalid-last-value",
    "exit_code": 1
  },
  {
    "case": "duplicate-json-key-has-no-value-winner",
    "exit_code": 1
  },
  {
    "case": "single-positive-drop-is-declared-not-measured",
    "exit_code": 1
  },
  {
    "case": "multiple-ends-with-one-valid-drop-still-ambiguous",
    "exit_code": 1
  },
  {
    "case": "line-of-sight-denominator-uses-only-booleans",
    "exit_code": 1
  },
  {
    "case": "bom-blank-unknown-fields-and-private-values",
    "exit_code": 1
  },
  {
    "case": "selected-files-stay-separate-without-pooling",
    "exit_code": 0
  },
  {
    "case": "identical-distinct-files-are-repeated-observations",
    "exit_code": 0
  },
  {
    "case": "repeated-rows-contribute-without-unique-entity-inference",
    "exit_code": 1
  },
  {
    "case": "refuse-same-file-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-generator-directory",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-input",
    "exit_code": 2
  },
  {
    "case": "refuse-unsupported-details-mode",
    "exit_code": 2
  },
  {
    "case": "refuse-physical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-decimal-exponent-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-nonblank-record-bound",
    "exit_code": 2
  }
]
```

The final summary records 22 cases: five exit 0, nine review exit 1 and eight
incomplete exit 2 results. Thirteen normal manifests cover 26 report payloads.
Fifteen selected-source hash observations, fifteen unchanged fictional fixtures
and 54 exact input/report files are independently checked.

All eight scope flags stay false: live collection, games launched, processes
monitored, real captures, capture completeness, unique entity inference, causal
diagnosis and runtime-performance verification. Counts describe supported saved
observations only. Read [FORMAT.md](docs/FORMAT.md) and
[QUALIFICATION.md](docs/QUALIFICATION.md) for the exact subset and release gates.

Use trusted stable inputs and owned output parents. Path/snapshot checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. An output failure can leave a partial new directory; preserve/review
it, fix the cause and choose a new destination for a retry. No real capture,
producer integration, session identity, lossless recording, game health or
runtime behavior is established here.
