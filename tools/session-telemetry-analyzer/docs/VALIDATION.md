# Validation and limits

Run from this module directory with CPython 3.12 or newer:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

The reviewed Windows/CPython 3.12.7 suite discovers 54 methods: 51 passed and
three platform/environment checks skipped, with no failures/errors. The count
includes 18 repeated first-party safeguard tests for standalone use. Hardlink
and symlink creation were unavailable in the restricted local environment;
POSIX FIFO behavior is a platform-only case. Skips are separate from passes.
Windows/Ubuntu CI supplies independent platform runs; consult the repository
Actions results and batch review for the actual matrix outcomes.

Generated fixtures cover independent sample denominators; explicit zero versus
missing/invalid values; exact count/boolean types; tracking/visibility partial
data; exact decimal time declarations and decreases; missing/positive/invalid
drop fields; duplicate start/end markers; unknown fields/types; duplicate JSON
keys and nonfinite constants; invalid envelopes; physical/decoded controls;
encoding/BOM/CRLF/blank/final-line conventions; empty input; record, node, number,
string and collection bounds; separate files and repeated records.

Actual CLI subprocess tests verify fixed exit/status codes, no source filename
or private payload emission, stable input bytes, fresh output refusal, duplicate
input aliases, report hashes, synthetic generator behavior and the documented
example statistics. Common safeguards also exercise path/regular-file rules,
change detection, links/reparse routes, byte/text/JSON limits, escaped static
HTML and unsigned report manifests.

For a constrained environment, set `TEMP` and `TMP` to an existing writable
private directory before running tests. Tests create and clean their own
temporary directories there. Production code never launches a subprocess;
tests launch only the authored Python CLI and fictional generator.

These tests validate a documented offline subset. They do not establish real
producer compatibility, capture authenticity/completeness, lossless recording,
unique entities, multiplayer synchronization, causal diagnosis or runtime
performance. No actual capture or game state was used for acceptance.
