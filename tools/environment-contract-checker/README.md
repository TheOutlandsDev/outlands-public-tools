# Environment Contract Checker

Check only explicitly declared prerequisites before following a setup guide.
Standalone 0.1.0 is source-only, for Windows/Ubuntu Python 3.12–3.15, standard
library only. The checker inspects selected file metadata
and searches selected program directories. It does not execute discovered
programs, read target file contents, import selected modules, install packages,
change PATH, probe a service, or collect host/account/hardware information.

A present candidate is not proof of a runnable executable, compatible runtime,
correct version, working permissions or a ready environment. Results describe
the declared checks at the time of observation.

Get selected source from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/environment-contract-checker-v0.1.0).
Keep `environment_check.py` and `environment_windows.py` adjacent and retain the
generator at `examples/make_fixture.py`. No interpreter, installed distribution,
runtime/dependency binary, generated program, actual environment record or raw
log is bundled. Supply Python separately; no pip dependency, model, account or
network service is needed. The [complete fictional guide](USAGE.md) checks full
JSON outcomes and input/runtime/prior-output preservation.

## Fictional example

From the extracted module directory, first define an absolute `$privateWork`
outside protected source with the [private workspace guide](docs/PRIVATE-WORKSPACE.md).
Create a fresh fixture under that existing private parent:

```text
python -B examples/make_fixture.py --destination "$privateWork/contract-fixture-001"
python -B environment_check.py --contract examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs"
```

Expected checker exit: **0**, `ALL_PRESENT`. The generator creates only a new
destination with `inputs`, `programs` and `workspace` directories, plus two
fictional files. It never replaces existing output or executes the program.
The generated program has a harmless nonzero exit code if explicitly run;
finding its metadata still satisfies the presence-only rule. Do not run it.
Generated scripts stay private and are not part of the source release payload.

To exercise a missing program, use the fixture's empty workspace as the search
directory while keeping the same file root:

```text
python -B environment_check.py --contract examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/workspace"
```

Expected exit: **1**, `REVIEW_REQUIRED`. This is a deliberate missing requirement.
Omitting a needed root/search selection produces `UNKNOWN` rather than proof
that the target is absent. An explicitly supplied root must be an existing
ordinary directory; an invalid or unavailable root returns `ERROR`. A selected
program directory that does not exist can yield `MISSING` because that selected
search scope is absent. Unsafe or uncertain paths retain `UNSAFE` or `UNKNOWN`.
No implicit PATH, PATHEXT or current-directory search is performed.

## Contract format

The UTF-8 JSON object contains exactly `schema_version` and `requirements`:

```json
{
  "schema_version": 1,
  "requirements": [
    {"id": "sample_file", "kind": "file", "path": "inputs/fictional.txt"},
    {"id": "sample_directory", "kind": "directory", "path": "workspace"},
    {"id": "sample_program", "kind": "program", "name": "fictional-tool"},
    {"id": "platform_review", "kind": "observation"}
  ]
}
```

IDs start with a lowercase ASCII letter, followed by lowercase letters, digits,
underscores or hyphens, at most 40 characters in total. File and
directory paths are canonical relative forward-slash paths beneath the selected
root. Program names are simple basenames rather than paths or shell commands.
Unknown fields, duplicate JSON keys/IDs, wrong types, traversal and unsafe path
forms are refused. No environment-variable or home-directory expansion occurs.

Program discovery uses only the explicit `--program-dir` selections. On Windows
it considers the static `.exe`, `.com`, `.bat` and `.cmd` candidate suffixes, not
the operator's PATHEXT. On POSIX the regular candidate also needs executable
permission. The checker does not establish executable format or actual startup
behavior on either platform. It does not enumerate unrelated files recursively.

## Operator observations remain unverified

Optional observations have exactly this shape:

```json
{
  "schema_version": 1,
  "observations": [
    {"id": "platform_review", "satisfied": true}
  ]
}
```

They carry a boolean attestation, not raw operating-system, architecture, version,
hostname or other environment strings. A supplied `true` does not become a
verified fact: observation checks always remain `UNKNOWN`, and a contract that
contains one returns `REVIEW_REQUIRED`. Fixed evidence codes distinguish
`OPERATOR_REPORTED_TRUE_UNVERIFIED`, `OPERATOR_REPORTED_FALSE_UNVERIFIED`, and
`OBSERVATION_NOT_SUPPLIED`. Those codes disclose the boolean attestation while
keeping it explicitly unverified; no arbitrary environment values are accepted.

```text
python -B environment_check.py --contract examples/observed-contract.json --observations examples/observations.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs"
```

Expected exit: **1**, with the three metadata-presence checks present and
`platform_review` still unknown/unverified.

## Results and private reports

Per-check results include only the ID, kind, fixed status and evidence class.
Statuses are `PRESENT`, `MISSING`, `UNKNOWN` and `UNSAFE`. An inaccessible or
unselected check is not silently treated as missing; linked/reparse paths,
hard-linked files and special nodes are not accepted as ordinary targets.
No target path, resolved candidate, program name, arbitrary observation string, environment
value, file content or native exception text appears in the result.

IDs are echoed verbatim. A syntactically valid ID can still identify a project,
and requirement statuses can reveal its environment. Choose neutral IDs and
keep operator contracts and reports private; this is not an anonymizer, secret
scanner, IP review or approval to publish operator inputs.

By default, JSON is written to stdout. For a private report, select a new file
outside protected source and all selected root/program directories, with an existing
parent:

```text
python -B environment_check.py --contract examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs" --report "$privateWork/contract-result-001.json"
```

Existing reports are refused. Report creation requires verifiable directory
identities to check the selected boundaries, including common path aliases;
unverifiable boundaries are refused. Restrictive file-mode requests do not
establish Windows ACL privacy. Exit `0` means `ALL_PRESENT`, exit `1` means
`REVIEW_REQUIRED`, and exit `2` means `ERROR`; none means a program was executed
or the environment was accepted for production.

Missing selected program directories remain protected report exclusions even
though their searches can yield `MISSING`. The checker creates none of them.
Requested reports must finish all write/readback/boundary guards before success;
a partial or complete-looking **unconfirmed new report** can remain on failure.
Existence or parseability is not completion. Retain it privately, require actual
exit/status and choose a new name for retry. No overwrite or automatic cleanup
occurs. Caller stdout redirection/capture has separate overwrite behavior.

Successful/review reports keep `target_contents_read`, `programs_executed` and
`versions_verified` false. Fixed checker errors carry the first two flags false;
the generator separately carries `fixture_executed: false`. Checker `--version`
already displays 0.1.0; the generator has no version option.

## Standalone repairs

Source-boundary constant blocks in the checker and fixture generator are
repaired for standalone placement. The checker derives its module directory;
the generator derives the module directory above `examples`. Literal
`tools/environment-contract-checker` placement protects the whole collection;
otherwise that module directory is protected. This is structural placement,
not Git-root discovery. The Windows report writer also refuses any observed
existing output leaf before exclusive CRT creation, including a dangling link.
All other function bodies are preserved; historical I/O-safety text and three
original JSON examples retain baseline bytes. Whole-byte identity for the three
code files is not claimed. Local Win1314 prevents a native dangling-link
reproduction; the guard's source ordering and applicable hosted fixtures must
be verified. This establishes no atomic/race/hostile-filesystem guarantee.

## Bounds and filesystem limits

Control-file and new-report I/O has a [current hardening review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-35-ENVIRONMENT-CONTRACT-IO.md)
and [platform checks/limits](IO-SAFETY.md). Windows requires the adjacent
`environment_windows.py`. Target probing remains
metadata-only; report readback reads only the new report. Schemas, prerequisite
decisions and report bytes are preserved. Missing protected program directories
remain reportable, while Windows I/O path checks are stricter.

Each control JSON input is limited to 64 KiB, a contract to 128 checks, and
program search to 16 explicit directories. Relative paths permit 240 characters
and 32 parts. Target probing is limited to 2,048 probes, with a five-second budget
checked between probes. A blocked filesystem call cannot be interrupted by
that between-probe check.

Use stable trusted local roots and parents. Symlink/reparse and type checks do
not freeze a tree or create a hostile-filesystem sandbox. Presence can change
after the observation. No socket/DNS or service-probe API is used, but filesystem
metadata calls on mapped drives or mounted shares can still involve the OS's
network storage stack. Remote-storage classification, arbitrary mounts,
concurrent writers and full Windows ACL behavior are not proven by these checks.

The fixture generator requires an ordinary existing private parent and a new
absolute destination outside protected source, with verifiable directory identities
for its source-boundary check. A failure can leave partial **new**
fictional output for inspection. It does not delete that output automatically,
relocate existing files or provide a general workspace/installation service.

Use fully spelled canonical trusted paths; metadata and control/report paths
have distinct checks. No blanket original-spelling/alias refusal is implied.
Fictional Windows probes on Python 3.12.7/3.15.2 rejected all leaf/parent trailing
dot/space forms for contract/observation controls. Root/program-directory and
external-report selections accepted leaf-dot, leaf-space and parent-dot forms
after normalization; parent-space returned `SELECTED_PATH_INVALID`. Generator
external destinations rejected all four aliases. Protected source report/fixture
outputs were refused in both layouts. The report-leaf guard checks an observed
existing leaf, not original-spelling aliases; these bounded observations establish
no universal alias/race/provider guarantee. Detailed outcomes belong to the
fictional guide and qualification receipts.
Requested POSIX file/directory/executable modes depend on OS/Python/ACL behavior,
not a confidentiality or encryption promise. The between-probe clock is not a
global deadline or total CPU/RAM/storage quota. Reads/metadata checks can affect
access metadata; blocked I/O, power loss and live/provider storage remain outside
acceptance.

Fresh qualification selects eight Windows/Ubuntu Python 3.12, 3.13, 3.14 and
3.15.2 lanes, with fresh no-pip/zero-distribution environments. It retains
103 originals (53 shared and 50 I/O) plus 30 copied checker/generator CLI methods:
**133 per lane, 1,064 selected executions**. Selection is not a passing result;
actual versions/counts/outcomes/named skips belong to release `VALIDATION.json`.
See [QUALIFICATION.md](docs/QUALIFICATION.md). Historical counts and the earlier
unchanged-generator/backend statements in `IO-SAFETY.md` are preserved history,
separate from the two scope repairs, report-leaf guard and fresh qualification.

## Provenance, licensing and validation

This is a fresh neutral implementation informed by selected owner-reported
prerequisite-checking methods. It contains newly authored source and fictional
fixtures. Original operational scripts, source mappings, private paths, keys,
credentials, configurations, host captures and third-party runtime payloads are
excluded. No original private setup script is copied or executed.

Selected original code and examples use the full [MIT license](LICENSE).
That grant does not relicense operator inputs, installed programs, operating
systems or future dependencies. Authorship is based on the owner's personal-work
statement and this fresh implementation, not independent proof of exclusive
ownership of all historical material. See the [batch review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-9-ENVIRONMENT-CONTRACT.md)
for actual test results, supported platforms and remaining validation limits.
Standalone preparation/qualification used AI assistance without exclusive-
authorship claims. User-owned Python/venvs need no inherent administrator access;
respect OS/device policy without bypasses. See [PROVENANCE.md](docs/PROVENANCE.md),
[third-party notices](THIRD-PARTY-NOTICES.md) and
[private workspace guidance](docs/PRIVATE-WORKSPACE.md).
