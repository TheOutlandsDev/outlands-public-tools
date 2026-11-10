# XML Recipe Inspector: Python 3.12–3.15 qualification

The earlier aggregate Windows run combined POSIX-specific shared assertions
with dedicated native Windows fixtures. It discovered 84 methods: one failure,
three errors and two skips. The failures came from numeric POSIX mode checks,
unavailable FIFO creation and missing local symlink privileges. Windows' native
refusals use different fixed error categories from POSIX. No parser or native
runtime change was needed; both runtime modules remain byte-identical to prior
public source.

Shared tests still verify source preservation, strict JSON and exclusive output
on both platforms, assert 0700/0600 only on POSIX and select each platform's
documented link-refusal code. FIFO is explicitly POSIX-only. Missing symlink
creation is a local skip but fails required hosted native qualification. DTD/
entity/PI rejection, resource bounds, numeric checks, geometry conventions,
CSV shielding and native file safeguards were not relaxed.

Five new fresh-process methods copy only the two runtime modules into private
fictional fixtures. Isolated/no-site children deny socket creation/connection,
process launches and shell calls, with guard selfchecks. They export/reopen
four overlay reports, preserve inputs/existing outputs, reject UTF-8/UTF-16
declarations before output, preserve JSON text while shielding CSV formulas,
and exercise help/argument redaction. No actual recipe/image/vendor application
is used. The local Windows/Python 3.15.2 suite then ran 89 methods: 84 passed,
five explicit platform/privilege skips, zero failures/errors. This is partial
local evidence, not full native acceptance. No security setting was changed.

The [platform workflow](https://github.com/TheOutlandsDev/outlands-public-tools/actions/workflows/xml-recipe-checks.yml)
builds a deterministic allowlisted source ZIP and rebuilds/compares its exact
bytes across Windows/Ubuntu × Python 3.12, 3.13, 3.14 and 3.15.2. Each lane runs
all 89 methods from a fresh extraction in a new venv without pip/dependencies.
Reports contain actual Python/Expat versions, ZIP digest, counts and explicit
skips. Native hardlink/symlink/junction execution is required. Only opposite-
platform cases and unavailable optional 8.3 spellings may skip.

The release's VALIDATION.json supplies actual hosted outcomes and the exact
digest. The ZIP has 17 members: 16 allowlisted text/source inputs and a generated
manifest. The full repository MIT notice is retained. Build and qualification
methods are included. Supply the selected regular CPython separately.

Reproduce from a reviewed committed checkout:

```text
python -B tools/xml-recipe-inspector/packaging/build.py --out NEW_ABSOLUTE_PACKAGE_DIRECTORY
python -B tools/xml-recipe-inspector/packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY --report NEW_ABSOLUTE_REPORT_JSON
```

Scratch paths must be outside the source tree under trusted local parents.
Reports describe software behavior on the named test hosts. They do not certify
vendor schema/measurement accuracy, ownership or release rights of future input,
hostile concurrency, ACL privacy, network/virtual storage or hardware durability.
