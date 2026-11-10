# Windows and Python 3.12–3.15 qualification

The previous aggregate Windows run combined a POSIX-specific original suite
with the dedicated portable/native Windows suite. It therefore failed on a
numeric mode-0600 assertion, unavailable POSIX FIFO creation, POSIX-specific
exception categories and local symlink privilege. These were test-contract and
host-capability issues; the four runtime files did not need a compatibility
change. No refusal, bound, identity check or output-protection rule was weakened.

The shared suite now keeps content/source/overwrite checks on both platforms,
asserts 0600 only on POSIX, checks Windows' documented missing/link rejection
codes and separates FIFO from traversal so traversal always runs. A missing
local Windows symlink privilege is explicit; CI requires the feature and fails
if it is unavailable. The native hardlink/junction suite remains mandatory.
POSIX retains every original behavioral assertion and error code.

Five new fresh-process tests copy only the four runtime modules into generated
private fixtures. Children use isolated, no-site Python with socket, process
launch and shell actions denied and self-checked. They exercise conversion/
validation, report preservation, exclusive output, invalid report/no output,
unsupported requirement refusal, help and argument redaction. No actual report,
artifact, package feed or install is used.

The [platform workflow](https://github.com/TheOutlandsDev/outlands-public-tools/actions/workflows/dependency-lock-checks.yml)
builds a deterministic source ZIP from an explicit committed text allowlist,
rebuilds/compares it on Windows and Ubuntu for Python 3.12, 3.13, 3.14 and
3.15.2, and runs all 81 methods in fresh venvs without pip/dependencies. Tests
import the extracted tool outside the checkout. Reports show exact interpreter
versions, digest, execution counts, legitimate platform/short-name skips and
unexpected skips. Native-feature skips cannot qualify Windows.

Local Windows 11/Python 3.15.2 initially discovered 75 methods: one failure,
five errors and two skips. The corrected 76-method suite passed 70 methods with
six explicit platform/privilege skips and zero failures/errors. The five added
copied-runtime CLI methods then passed independently. This partial local result
does not substitute for native-link execution on the hosted test runners. No
privilege, Developer Mode, policy, firewall or service change was made.

The release's VALIDATION.json supplies actual hosted results and the exact ZIP
digest. The source ZIP has 19 members: 18 allowlisted text/source inputs and a
generated digest manifest. LICENSE retains the repository MIT notice. Nothing
is installed by extracting it; Python is supplied separately.

Reproduce from a reviewed committed checkout:

```text
python -B tools/dependency-lock-tools/packaging/build.py --out NEW_ABSOLUTE_PACKAGE_DIRECTORY
python -B tools/dependency-lock-tools/packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY --report NEW_ABSOLUTE_REPORT_JSON
```

Only generated disposable files are changed. Keep scratch space outside the
source tree under a trusted local parent. File/format fixtures do not establish
artifact authenticity, a resolved environment, an install plan, hostile-race
containment, live network filesystem support or hardware durability.
