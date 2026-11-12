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

The cumulative ledger is **216 tools with passing source-suite observations**:
182 from the original review plus 29 shared-suite tools, one recovered native
launcher, the subsequently qualified safe file mover, Resource Monitor and
Dependency Lock Tools and XML Recipe Inspector. This combines baseline and follow-up evidence, not a fresh 216-tool
rerun. The `tools/` and shared `tests/` sources were unchanged between the baseline
checkout and follow-up base `db011c763dd3f5e4712f793b5ccda86bf7eea875`, before
the retention fix. The safe mover's removed reserved-name API was then fixed;
its [separate review](../../tools/safe-file-mover/docs/PYTHON315.md) records
strict Windows/Ubuntu Python 3.12, 3.13 and 3.15.2 fixture qualification. Its
standalone 0.2.1 wheel adds fresh Windows/Ubuntu installs for Python 3.12–3.15;
see its [usage and release evidence](../../tools/safe-file-mover/USAGE.md).
Resource Monitor's Python 3.12/3.13-only launcher guard now accepts 3.12–3.15.
The Windows/Python 3.15.2 source run with psutil 7.2.2 passed 53 of 54 methods,
with one explicit symlink-privilege skip and no failures/errors. This local
observation is partial; its [separate download qualification](../../tools/resource-monitor/docs/PYTHON315.md)
requires eight fresh extracted-ZIP lanes with demo/live in separate venvs and
mandatory native features before publication. The release's VALIDATION.json
records actual hosted results. No native readings or tokens are published.
Dependency Lock Tools' aggregate Windows failures were POSIX-only permission/
FIFO assumptions, platform-specific rejection codes and unavailable local
symlink privilege. Its four runtime modules remain unchanged; shared tests now
assert each platform's contract. Local Python 3.15.2 passed the corrected suite
and five copied-runtime CLI cases, with six explicit platform/privilege skips.
Its [fresh extracted-package qualification](../../tools/dependency-lock-tools/docs/PYTHON315.md)
requires eight Windows/Ubuntu Python 3.12–3.15 lanes with mandatory native links;
the release's VALIDATION.json records actual hosted counts. This does not
qualify real package artifacts or an installation plan.
XML Recipe Inspector's shared tests now apply each platform's permission/error
contract, with FIFO explicitly POSIX-only and native links mandatory in hosted
qualification. Both runtime modules remain unchanged; parser/entity/resource
and file safeguards are retained. Local Windows/Python 3.15.2 ran 89 methods:
84 passed, five explicit platform/privilege skips, zero failures/errors. Its
[fresh extracted-package qualification](../../tools/xml-recipe-inspector/docs/PYTHON315.md)
requires all eight OS/Python lanes before publication; the release's
VALIDATION.json gives actual patches, Expat versions, counts and skips. These
checks do not establish vendor measurement accuracy or rights to future input.
The older collection/bundle contracts remain unchanged.

PDF Text Bounds Inspector 0.2.0 follows up the dependency refusal recorded below.
The unchanged original pins again passed 54 of 56 methods on local Windows
Python 3.15.2 (two platform/privilege skips). The recorded newer combination
reproduced 38 unsuccessful methods: 13 assertions and 25 errors, all blocked by
the exact-version guard before geometry work. The updated reviewed pins are
`pypdfium2==5.15.2` and test-only `pypdf==7.0.1`; seven other runtime pins stay
unchanged. The guard and inspection logic remain intact. Local updated source
ran 62 methods: 60 passed, two explicit skips, zero failures/errors.

Its [fresh dependency/source ZIP qualification](../../tools/pdf-text-bounds/docs/PYTHON315.md)
requires all eight Windows/Ubuntu Python 3.12-3.15 lanes before publication.
Each installs runtime and dev dependencies from wheel SHA-256 locks into a new
venv, tests runtime-only CLI behavior before adding test-only pypdf, checks a
deliberately bad hash is refused, and runs the full authored-PDF suite. Actual
patch versions, wheel hashes and skip counts appear in the release's
VALIDATION.json. This single-tool update does not requalify all collection
dependencies, wheel/bundle requirements or real/private PDFs.

Together, 216 cumulative passing source-suite observations and six
separate platform workflows account for the 222 tool directories. The PDF
follow-up does not add another directory or represent a fresh all-tool rerun.

ZIP Package Policy Verifier 0.1.0 now has a separate
[standalone download qualification](../../tools/zip-package-policy/docs/QUALIFICATION.md).
Its CLI is PowerShell, with no Python runtime dependency. The unchanged baseline
ran all 60 generated harness cases locally on Windows/PowerShell 7.6.9.
The standalone release requires four fresh Windows/Ubuntu lanes using official
hash-pinned PowerShell 7.6.10 LTS and 7.7.0 stable. Each runs the original cases
and nine copied-runtime CLI methods, with native links mandatory in hosted CI.
Eight additional Python 3.12-3.15 helper lanes reproduce exact source ZIP bytes.
The release's VALIDATION.json records actual runtime versions, hashes, counts
and skips. This qualifies one of the six separate-runtime tools; the cumulative
216 Python-source observations and older wheel/bundle requirements stay unchanged.

FFmpeg Capture Log Inspector 0.1.0 has a separate
[saved-log download qualification](../../tools/ffmpeg-log-inspector/docs/QUALIFICATION.md).
Its unchanged PowerShell inspector reads authored saved logs without FFmpeg,
media, capture devices or a Python CLI dependency. Four fresh Windows/Ubuntu
lanes use pinned PowerShell 7.6.10 LTS and 7.7.0 stable prerequisites; native
symlink refusal is mandatory. Eight Python 3.12-3.15 source/build helper lanes
reproduce identical ZIP bytes and verify optimized-Python refusal before helper
operations. The release's VALIDATION.json records actual case/method counts,
runtime archive digests, interpreter patches and skips. This is parsing evidence,
not proof of recording/playback quality, device health or process completion.
The cumulative 216 Python-source observations and older bundle requirements
remain unchanged.

Hash Journal 0.2.0 adds a separate
[modern .NET source-download qualification](../../tools/hash-journal/docs/QUALIFICATION.md).
The default target is .NET 10, with explicit .NET 11 qualification using pinned
SDKs 10.0.404 and 11.0.100 on Windows/Ubuntu x64. The version-one format, golden
hashes and core journal implementation remain unchanged; the native fixtures
now enforce mandatory symlink coverage in hosted CI and record every skip.
Four fresh extracted-source build/runtime lanes and eight Python 3.12-3.15
source/build helper lanes are required before release. The release's
VALIDATION.json records actual targets, SDK/archive hashes, counts and skips.
Python is a maintainer helper, not a Hash Journal runtime dependency. This does
not add another Python-source observation to the cumulative 216 or change older
wheel/bundle requirements. Consistency and externally anchored checks do not
establish the events' author, truth or timestamps.

.NET Public API Diff 0.1.0 adds a separate
[source-download qualification](../../tools/dotnet-api-diff/docs/QUALIFICATION.md).
Four fresh Windows/Ubuntu SDK/runtime lanes use pinned SDKs 10.0.404 and
11.0.100, targeting the CLI, test harness and both fictional assembly projects
together. Metadata inspection, the report format and golden declarations are
preserved; native links are mandatory in hosted qualification. Eight Python
3.12-3.15 helper lanes reproduce exact source ZIP bytes and exercise optimized
Python refusal. Actual SDK/archive identities, targets, cases and skips appear
in the release's VALIDATION.json. Python is a maintainer helper, not a CLI
runtime dependency. These results do not add to the cumulative 216 Python
source-suite observations or establish full binary/runtime compatibility or
safety for hostile metadata.

Source Inventory 0.1.0 has a separate
[standalone source-download qualification](../../tools/source-inventory/docs/QUALIFICATION.md).
All three runtime modules remain unchanged. The original 124 inventory, tree,
classifier and Windows safety methods retain their assertions, with stricter
native-fixture setup and skip handling. Eight fresh Windows/Ubuntu Python
3.12-3.15 lanes exercise those regressions and copied three-file runtime CLI
processes in new venvs without pip or third-party distributions. Each lane
reproduces the exact ZIP/build-manifest bytes and tests optimized-Python refusal
in the two maintainer helpers. The release's VALIDATION.json records actual
interpreter patches, counts and every platform/optional-short-name skip.
Native links and junctions are mandatory where applicable in hosted acceptance.
Real trees/reports remain private. This does not add another directory to the
cumulative 216 Python-source observations or qualify live/hostile filesystems,
provider behavior, confidentiality or whole-tree publication rights.

Documentation Check 0.1.0 adds a separate
[standalone source-download qualification](../../tools/documentation-check/docs/QUALIFICATION.md).
Both runtime modules remain unchanged. The five original shared documentation
methods are retained in a minimal standalone fixture with matching method ASTs;
the original shared file remains unchanged. Together with the 40 I/O methods
and copied two-file CLI checks, eight fresh Windows/Ubuntu Python 3.12-3.15 lanes
validate the bounded offline checks in new no-pip/no-distribution venvs. Each
lane compares exact source ZIP/build-manifest bytes and checks both packaging
helpers refuse optimized Python. The release's VALIDATION.json records actual
versions, counts, required platform skips and any confirmed short-name absence.
Applicable native links/junctions remain mandatory in hosted acceptance.
This is documentation hygiene, not full Markdown/JSON-schema validation or
secret/IP clearance. It does not add another directory to the cumulative 216
source observations or requalify older bundles and their Python requirements.

Python Helpers 0.1.0 adds a separate
[standalone source-download qualification](../../tools/python-helpers/docs/QUALIFICATION.md).
Both runtime modules and the retained input contract remain unchanged. Five
original shared helper methods are isolated with identical method ASTs alongside
the 40 input methods. Eight fresh Windows/Ubuntu Python 3.12-3.15 lanes exercise
these regressions and copied-library API consumers in no-pip/no-distribution
venvs, verify extracted imports and fixed runtime hashes, compare independently
rebuilt ZIP/build-manifest bytes, and reject optimized release helpers. Exact
versions, counts and named platform/short-name skips are in the release's
VALIDATION.json; hosted native links/junctions remain mandatory where applicable.
JSON and redaction semantics are retained, including duplicate-key and float
behavior. Redaction does not anonymize free text, unknown fields or identities.
Actual inputs/results remain private. This does not add to the cumulative 216
source observations or requalify older bundles or their Python requirements.

Project Workspace 0.1.0 adds a separate
[standalone source-download qualification](../../tools/project-workspace/docs/QUALIFICATION.md).
The CLI/POSIX/template source and retained filesystem contract remain unchanged.
The Windows backend adds an observed-output-leaf refusal before the CRT exclusive
open, preventing the checked dangling-link case from creating its missing target.
Six original shared workspace methods are isolated with identical method ASTs
alongside the 40 portable/native methods. Eight fresh Windows/Ubuntu Python
3.12-3.15 lanes exercise these regressions and copied-runtime CLI consumers in
no-pip/no-distribution venvs, verify extracted imports and fixed runtime hashes,
compare independently rebuilt ZIP/build-manifest bytes, and reject optimized
release helpers. Exact versions, method counts and named platform/short-name
skips are in the release's VALIDATION.json. Applicable hosted native links and
junctions remain mandatory. A separate Windows comparison requires the same
unchanged regression to expose the pinned pre-fix failure and pass on reviewed
source; those two diagnostic executions are separate from the eight-lane counts.
Lane runtime-stability flags refer to the reviewed release hashes during tests,
not equality of the patched backend with historical source. Plan mode can read a selected input but creates
nothing and reserves no name; failed creation can retain partial or
complete-looking unconfirmed private output. The original layout, template,
opaque copies, source bounds and platform behavior are retained. Generated
workspaces and actual inputs remain private. This does not add to the cumulative
216 source observations or requalify older bundles or their Python requirements.

Public Release Audit 0.1.0 adds a separate
[standalone source-download qualification](../../tools/public-release-audit/docs/QUALIFICATION.md).
The full CLI/detector/POSIX source and historical filesystem contract remain
preserved. Nineteen original shared audit methods are isolated with identical
method ASTs alongside 40 I/O methods. Eight fresh Windows/Ubuntu Python 3.12-3.15
lanes exercise these regressions and copied-runtime CLI cases in no-pip,
no-distribution venvs, verifying extracted imports, reviewed runtime hashes,
independent ZIP/build-manifest bytes and optimized-helper refusal. Dangling
report and manifest output targets receive explicit native coverage. Exact
versions, discovered methods and named platform/short-name skips are recorded
in the release's VALIDATION.json. Frozen/current auditor comparisons and manual
review remain separate from pattern findings. Actual exports, private markers,
reports and manifests stay private; a no-pattern result is not confidentiality,
IP or behavior clearance. This does not add to the cumulative 216 observations
or requalify older bundles and their Python requirements.

Package Layout Checker 0.1.0 adds a separate
[standalone source-download qualification](../../tools/package-layout-checker/docs/QUALIFICATION.md).
Both runtime modules and the 33-method POSIX test file remain unchanged. All
64 original test-method ASTs are preserved while native fixture failures and
short-name absence receive stricter handling. Eight fresh Windows/Ubuntu
Python 3.12-3.15 lanes run those regressions and 26 copied two-file runtime CLI
methods in new no-pip/no-distribution venvs. The original POSIX descriptor suite
is explicitly unsupported on Windows; all 33 methods must run on Ubuntu, and
applicable Windows native link/junction fixtures are mandatory in hosted lanes.
Each lane reproduces exact ZIP/build-manifest bytes and checks both packaging
helpers reject optimized Python. Actual versions, counts and every named skip
appear in the release's VALIDATION.json. The historical Windows contract keeps
its wording with one link updated for standalone use. Manifest rules and output
filenames can be private; only declared files are checked, with no selected-source
execution, network or package writes. This does not add another directory to the
cumulative 216 observations or establish exact-export, dependency or privacy
clearance for a real package.

Dependency Lock Diff 0.1.0 adds a separate
[standalone source-download qualification](../../tools/dependency-lock-diff/docs/QUALIFICATION.md).
Its single runtime script, original shared suite, existing attributes and five
fictional example files retain exact Git bytes, including BOM/newline variants.
All 41 original method ASTs, 86 assertions and the static legacy-validator helper
are retained in a standalone adapter. Two exact published Dependency Lock Tools
modules are pinned only as test fixtures for the unchanged 100-valid/20-malformed
parser-parity cases; the CLI has no sibling-module or third-party dependency.
Eight fresh Windows/Ubuntu Python 3.12-3.15 lanes run those regressions and 26
copied-single-script CLI methods in new no-pip/no-distribution environments.
Each requires applicable native fixtures, identical ZIP/build-manifest rebuilds,
verified validator pins and non-skipped parity cases, plus optimized-Python
refusal in both packaging helpers. The release's VALIDATION.json records actual
patches, counts and every named skip. The checker compares declarations only:
version text is not ranked, hashes are not artifact verification, and results
are not installation, environment or vulnerability advice. Real package names,
versions, hashes, comments and outputs remain private. This does not add a
directory to the cumulative 216 observations or requalify older bundles.

Source Inventory Diff 0.1.0 adds a separate
[standalone source-download qualification](../../tools/source-inventory-diff/docs/QUALIFICATION.md).
Its single runtime script, original shared test source and all seven example
files retain their exact Git bytes. The existing `* -text` attributes preserve
the captured CSV bytes and recorded hashes. All 45 original method ASTs and 97
assertion calls are retained in a standalone adapter; a pinned published Source
Inventory generator pair is included only as test fixtures for the unchanged
producer-compatibility case, with no additional CLI dependency.
Eight fresh Windows/Ubuntu Python 3.12-3.15 lanes run those regressions and 26
copied-single-script CLI methods in new no-pip/no-distribution environments.
Each requires applicable native link fixtures, exact ZIP/build-manifest rebuilds,
verified producer pins and the non-skipped compatibility case, plus optimized-
Python refusal in both packaging helpers. Actual patches, counts and named skips
are recorded in the release's VALIDATION.json. The checker reads only supplied
saved-report controls; differences and hash/size hints do not verify source-body
changes, renames, complete coverage, authenticity or publication rights. Real
filenames, timestamps, digests and outputs remain private. This does not add a
directory to the cumulative 216 observations or requalify older bundles.

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
