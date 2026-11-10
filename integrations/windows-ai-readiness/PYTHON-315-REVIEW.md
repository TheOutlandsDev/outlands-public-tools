# Python 3.15 source compatibility ledger

## Follow-up: shared suites and native interpreter qualification

The original per-tool runner looked only for `tools/TOOL/tests/test_*.py`.
Its 35 NO_TESTS results were discovery gaps, not evidence that no tests exist.
Twenty-nine tools are covered by fourteen shared suites in top-level `tests/`.
The other six use separate platform workflows: `dotnet-api-diff`,
`ffmpeg-log-inspector`, `friendlies`, `hash-journal`, `local-site-builder`, and
`zip-package-policy`. They remain outside this Python-suite qualification.

The shared suites now pass on Windows with Python 3.15.2: 421 unittest methods
ran, with nine explicit skips. Four additional runner guard tests verify that
zero discovered tests, wholly skipped suites, and real failures cannot qualify.
The [sanitized results](PYTHON-315-SHARED-RESULTS.json) preserve each suite's
tool associations, test counts, and skipped counts without machine paths or logs.

This run found an actual contract mismatch in `backup-retention-planner`:
newer `datetime.fromisoformat` accepts `24:00:00` as next-day midnight, while the
planner's schema requires canonical hours 00-23. Explicit clock-range checks
restore that contract. The existing two failing timestamp subcases now pass;
the 39-method retention suite also passes on Python 3.12.7 with two skips.

`app-affinity-launcher` additionally passed 74 methods with three skips using
the base Python 3.15.2 interpreter and disposable local NTFS fixtures. The earlier
virtual-environment executable forwarded to another process, invalidating the
fixture's direct-process PID expectation. This result qualifies the tested base
interpreter; it does not establish control over arbitrary spawned descendants.

The cumulative ledger is **213 tools with passing source-suite observations**:
182 from the original review plus 29 shared-suite tools, one recovered native
launcher and the subsequently qualified safe file mover. This combines baseline
and follow-up evidence, not a fresh 213-tool
rerun. The `tools/` and shared `tests/` sources were unchanged between the baseline
checkout and follow-up base `db011c763dd3f5e4712f793b5ccda86bf7eea875`, before
the retention fix. The safe mover's removed reserved-name API was then fixed;
its [separate review](../../tools/safe-file-mover/docs/PYTHON315.md) records
strict Windows/Ubuntu Python 3.12, 3.13 and 3.15.2 fixture qualification. Its
package-install metadata remains unchanged. Three tools remain unqualified:

| Tool | Follow-up boundary |
| --- | --- |
| `resource-monitor` | Two launcher tests still fail at its supported-runtime guard. |
| `dependency-lock-tools` | Windows runs still fail link/metadata cases and a POSIX numeric-permission expectation. |
| `xml-recipe-inspector` | Windows runs still fail symlink setup and a POSIX numeric-permission expectation. |

Together, 213 passing observations, three unqualified Python tools, and six
separate platform workflows account for the 222 tool directories. The newer PDF
library combination described below is also unqualified; a pinned source pass
does not establish compatibility with every newer dependency.

Run the shared qualification from the collection root on Python 3.15:

```text
python -B integrations/windows-ai-readiness/check_shared_python315.py
```

Optional `--report` writes structured counts to an explicitly selected file;
`--log-dir` writes private diagnostics and may contain local paths. Keep those
logs outside the public checkout. The runner uses fixed reviewed suite names,
separate processes, a 180-second timeout per suite, and no extra dependencies.

Use an ordinary local temporary directory for the fictional input fixtures.
The dedicated CI job sets TEMP, TMP and OUTLANDS_TEST_TEMP to the runner's
provided temporary directory. A junction-backed temp path makes the strict
modular readers correctly return LINKED_PATH; a disposable local junction
reproduced that failure. Do not relax the readers to accommodate such a path.

The [dedicated workflow](../../.github/workflows/python315-shared-tools.yml)
repeats shared qualification on Windows/Ubuntu and base-interpreter affinity
checks on Windows, using Python 3.15.2. Consult its actual CI results. These
checks do not change the released wheel requirements or validate original drive
data, installation permission, live services, or whole-machine readiness.

## Original baseline, retained for comparison

Checked on Windows 11 with Python 3.15.2 on 2026-11-09. This is a separate
compatibility exercise. The 76 released independent wheels, nineteen group
wheels, and selector still all declare `Requires-Python: >=3.12,<3.14`.
Their supported install and CI lanes remain Python 3.12/3.13.

All 1,595 Python source/test files under `tools/` parsed with the Python 3.15
AST parser without syntax errors. The 222 catalog tool directories were then
run as separate test roots to avoid collisions between repeated module names.
The first isolated pass had 179 passing tool suites, eight failing suites,
and 35 directories without `tests/test_*.py` files. After installing the
declared or current PDF/document dependencies and rerunning three affected
suites, 182 tool suites passed, five still failed, and 35 had no matching test
suite. Passing suites can contain explicit skips; these counts are by tool
directory, not individual test method.

| Tool at the initial review | Original observed boundary |
| --- | --- |
| `app-affinity-launcher` | Four native process/affinity tests failed, including a process ID mismatch. |
| `dependency-lock-tools` | Six tests failed; symlink creation returned Windows privilege error 1314 in the sandbox. |
| `resource-monitor` | Two launcher tests failed because its supported-runtime guard rejects Python 3.15. |
| `safe-file-mover` | 57 native filesystem tests failed, including named-stream cases; this environment cannot establish its Windows behavior. |
| `xml-recipe-inspector` | Four tests failed, including symlink creation blocked by Windows privilege error 1314. |

`document-builders` passed 64 tests with eight skips after its dependencies
were installed. `portfolio-builder` passed 41 with one skip after installing
`pypdf`. `pdf-text-bounds` passed 54 with two skips using its declared
development pins, including `pypdfium2==5.14.0` and `pypdf==6.21.2`.
With newer `pypdfium2==5.15.2` and `pypdf==7.0.0`, that suite had 38
failures, so its exact dependency pins matter. The newer dependency set was
not substituted into the released tool.

This review establishes Python 3.15 syntax and isolated test observations;
it does not certify the 76 wheel installs on 3.15, all Windows native features,
or every newer library version. Do not use `--ignore-requires-python` to turn
an unsupported wheel into a claimed supported installation.
