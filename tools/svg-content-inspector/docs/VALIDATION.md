# Validation record — 2026-10-25

The local fixture run uses the bundled **Python 3.12.14 / Expat 2.8.3** on Windows,
with warnings treated as errors. The older default Python 3.12.7 / Expat 2.6.3
is intentionally refused by the public parsing API; it was not used to bypass
the version check. See the current
[GitHub Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for Ubuntu Python 3.12/3.13 and Windows Python 3.13/3.14 outcomes.

The first hosted Windows 3.12 job selected CPython 3.12.10, whose Expat did not
meet the required minimum. The guard correctly failed before parsing. Windows
CI now selects maintained 3.13/3.14 binaries; the Expat check and all SVG tests
remain mandatory. The updated bundled Windows 3.12.14 run above is separate local
evidence, not a claim that the older hosted image passed.

The final local suite discovered **59 methods: 56 passed and three skipped**
(two Windows symbolic-link privilege cases and one POSIX FIFO case), with no
failures, errors or warnings. The actual clean CLI example returned 0 with one
unique internal reference and no findings. The review CLI returned the expected
1 with three reference observations and ten review findings. Both reports'
manifest lengths/hashes were independently verified. No source SVG was rendered.

The suite uses authored markup, mocked failure conditions and new temporary
ordinary files. It never renders any SVG or opens its references. Cases cover
namespace/root spoofing, exact decimal dimensions, units and unsupported values,
DTD/entity refusals, old Expat refusal, malformed XML/UTF-8, callback limits,
active/foreign/unknown markup, events/images, opaque/private details, duplicate
IDs, exact/missing/ambiguous fragments, base URLs and dual href declarations,
literal CSS URL/import observations, comments/strings/escapes/CDATA, explicit
CSS uncertainty, no reference file/socket access, report escaping, consistency
manifests, CLI statuses, safe errors, original bytes, changed/replaced sources,
nonregular/link paths, byte/output bounds and partial-output failure.

Windows without symbolic-link privilege skips the two native link fixtures;
the POSIX FIFO fixture is also skipped there. Linux requires native link creation
and exercises the FIFO refusal. `OUTLANDS_REQUIRE_SYMLINK_TEST=1` makes native
link creation mandatory on other hosts too. Skips are reported, never counted
as passes. The fictional generator and actual clean/review CLI commands are
checked separately against their documented exit statuses and report manifests.

An initial privacy test searched for the generic word `thing`, which also occurs
inside the inspector's explanation `Nothing was rendered`. The fixture now uses
a unique invented foreign-element identifier so it checks the intended private
name omission. No source disclosure guard was weakened. Unit normalization and
CSS escape coverage are tested explicitly.

Actual browser review also found that applying control-character escaping to
generated JSON indentation displayed its line breaks as literal escape text.
The report now preserves trusted JSON formatting newlines while JSON/HTML still
escape input values, and raw table cells still display control characters
explicitly. A focused layout/control fixture prevents that regression.

These checks establish the supported static inspection behavior, not a browser
security analysis, renderer sandbox, complete SVG/CSS validator, sanitizer,
accessibility test, visual acceptance or license determination. Real artwork and
private document data are not fixtures. Existing local QA source remains unchanged.
