# Python Helpers

Two small standard-library APIs load a bounded local JSON object and make a
separate redacted structure. This is a **library**, with no CLI, installer,
service or background job. Import the explicitly selected source module from
your own application; input JSON is never imported or executed as Python.

Download the initial **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/python-helpers-v0.1.0),
extract it into a fresh folder and follow [USAGE.md](USAGE.md). Keep
`helpers.py` and `helpers_windows.py` adjacent. Use Python **3.12–3.15**;
qualification selects 3.15.2 for that minor. No pip packages, network, model or
account are required. No interpreter, dependency binary, original private helper,
actual JSON/results or raw diagnostics are bundled.

| API | Result and limits |
| --- | --- |
| `load_json_object(path, max_bytes=1024*1024)` | Returns a decoded JSON object. Default 1 MiB; explicit positive integer override up to 16 MiB. |
| `redact_structure(value, *, max_depth=32)` | Returns separate nested mappings/lists with selected values replaced by `<redacted>`. Depth must be an integer from 1 through 128. |
| `HelperError` | `ValueError` subclass with fixed message strings; callers decide handling/output. |

The loader accepts UTF-8 with an optional BOM, requires an object and keeps
default duplicate-key behavior (**last value wins**). NaN/infinity literals
are refused. Standard decoder number/exponent behavior is unchanged: exponent
overflow is not a finite-number policy. Invalid limits raise `INVALID_LIMIT`
before I/O; read/parse/type failures raise `JSON_OBJECT_LOAD_FAILED` with
suppressed display context. `KeyboardInterrupt` propagates while owned handles
close. There are no library exit/status codes or automatic retries/cleanup.

## Redaction is a narrow key policy

Sensitive keys are `password`, `api_key`, `authorization`, `secret`, `token`,
`access_token`, `refresh_token`, `secret_key` and `private_key`. Matching uses
`casefold()` and replaces hyphens with underscores; output key spelling is
preserved. It does not strip spaces or discover new secret-key names.

The function copies encountered dictionaries/lists and preserves supported
primitive values. Unknown keys, free text and identifying metadata remain.
Existing float behavior, including nonfinite floats supplied by the caller,
is preserved. Unredacted unsupported types, nonstring mapping keys or excessive
nesting raise fixed `HelperError` strings. Sensitive-key values are replaced
without inspecting their contents. Read the exact
[input contract](docs/INPUT-CONTRACT.md).

**Redaction does not make arbitrary data safe to publish.** Fixed messages do
not anonymize caller tracebacks, caught exception objects, decoded values or
logs. Keep actual inputs, results and captures private. Application-specific
finite-number, schema, privacy and rights rules remain the caller's responsibility.

## Files, privacy and qualification

Select stable ordinary files under trusted quiescent local parents. Observed
symlink/reparse paths, parent traversal, special files and unsupported Windows
spellings/providers are refused. Hardlinked ordinary sources remain supported.
Windows loading uses the adjacent native backend; POSIX uses available
no-follow/nonblocking flags and descriptor/identity checks. Only unnamed data
is read; ADS, ACLs, ownership and topology are outside scope.

The loader writes no selected input/report/output. Reads may affect OS access
metadata, and Python can manage import caches separately. Byte limits are not
total CPU, memory, JSON-depth, result-size or elapsed-time quotas. Sampled checks
have race windows; they are not atomic snapshots, hostile-filesystem containment,
universal I/O timeouts, remote/live-provider or power-loss acceptance.

[USAGE.md](USAGE.md) gives explicit imports and a fictional private JSON → load →
redact walkthrough with structured caller outcomes and input/runtime hash checks.
Use an external [private workspace](docs/PRIVATE-WORKSPACE.md). User-owned
Python/venvs do not inherently need administrator access; respect device policy
without bypasses.

Eight fresh extracted-ZIP Windows/Ubuntu Python lanes use no-pip/no-distribution
venvs, the five original shared regression bodies, 40 existing input methods
and real copied-library consumer processes. Actual counts/outcomes/skips belong
to release `VALIDATION.json`, not planned coverage. See
[qualification](docs/QUALIFICATION.md) and the separate historical
[input contract/evidence](docs/INPUT-CONTRACT.md).

Selected original source is [MIT licensed](LICENSE), with retained notices and
AI-assisted preparation, without an exclusive-authorship claim. Read
[provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and the [earlier review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-29-PYTHON-HELPERS-HARDENING.md).
[Report an issue](https://github.com/TheOutlandsDev/outlands-public-tools/issues)
with authored fictional data and complete API outcomes. Do not attach real JSON,
personal paths, caught private exception objects or unreviewed redacted output.
