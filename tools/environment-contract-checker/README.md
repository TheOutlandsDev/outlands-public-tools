# Environment Contract Checker

Check only explicitly declared prerequisites before following a setup guide.
Python 3.12+, standard library only. The checker inspects selected file metadata
and searches selected program directories. It does not execute discovered
programs, read target file contents, import selected modules, install packages,
change PATH, probe a service, or collect host/account/hardware information.

A present candidate is not proof of a runnable executable, compatible runtime,
correct version, working permissions or a ready environment. Results describe
the declared checks at the time of observation.

## Fictional example

From the collection root, first define an absolute `$privateWork` outside the
entire checkout with the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md).
Create a fresh fixture under that existing private parent:

```text
python -B tools/environment-contract-checker/examples/make_fixture.py --destination "$privateWork/contract-fixture-001"
python -B tools/environment-contract-checker/environment_check.py --contract tools/environment-contract-checker/examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs"
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
python -B tools/environment-contract-checker/environment_check.py --contract tools/environment-contract-checker/examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/workspace"
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
python -B tools/environment-contract-checker/environment_check.py --contract tools/environment-contract-checker/examples/observed-contract.json --observations tools/environment-contract-checker/examples/observations.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs"
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
outside the checkout and all selected root/program directories, with an existing
parent:

```text
python -B tools/environment-contract-checker/environment_check.py --contract tools/environment-contract-checker/examples/contract.json --root "$privateWork/contract-fixture-001" --program-dir "$privateWork/contract-fixture-001/programs" --report "$privateWork/contract-result-001.json"
```

Existing reports are refused. Report creation requires verifiable directory
identities to check the selected boundaries, including common path aliases;
unverifiable boundaries are refused. Restrictive file-mode requests do not
establish Windows ACL privacy. Exit `0` means `ALL_PRESENT`, exit `1` means
`REVIEW_REQUIRED`, and exit `2` means `ERROR`; none means a program was executed
or the environment was accepted for production.

## Bounds and filesystem limits

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
absolute destination outside the checkout, with verifiable directory identities
for its checkout-boundary check. A failure can leave partial **new**
fictional output for inspection. It does not delete that output automatically,
relocate existing files or provide a general workspace/installation service.

## Provenance, licensing and validation

This is a fresh neutral implementation informed by selected owner-reported
prerequisite-checking methods. It contains newly authored source and fictional
fixtures. Original operational scripts, source mappings, private paths, keys,
credentials, configurations, host captures and third-party runtime payloads are
excluded. No original private setup script is copied or executed.

Selected original code and examples use the repository's [MIT license](../../LICENSE).
That grant does not relicense operator inputs, installed programs, operating
systems or future dependencies. Authorship is based on the owner's personal-work
statement and this fresh implementation, not independent proof of exclusive
ownership of all historical material. See the [batch review](../../docs/BATCH-9-ENVIRONMENT-CONTRACT.md)
for actual test results, supported platforms and remaining validation limits.
