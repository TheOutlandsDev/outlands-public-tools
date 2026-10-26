# Verified Binary Patch Planner

Preview explicitly declared, equal-length byte edits in a small local file.
Validate the complete selected source SHA-256 and size, expected bytes, edit
ranges and overlap before calculating a candidate output. Preview is the default.
The optional `--apply-output` argument creates a **separate new file**, reads it
back and verifies its bytes and SHA-256. The source and plan are never edited.

Original [MIT source](LICENSE), Python **3.12 or newer**, standard library only.
Useful for reproducible small binary-format experiments and reviewed byte-edit
recipes. This is not a format-aware game, firmware, executable or security
validator. A matching hash/plan does not establish ownership, authenticity,
safety, compatibility or an intended behavioral change.

## Install and try fictional examples

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/binary-patch-planner`. No package installation, admin access or
game/device installation is required. Keep the complete module folder when
using it standalone. Choose an existing absolute private work directory outside
the checkout. Every generated output directory/file must be new.

Windows PowerShell, after setting `$privateWork` to your existing private directory:

```powershell
python --version
python -B examples/generate.py --output "$privateWork/patch-demo"
python -B binary_patch_planner.py --source "$privateWork/patch-demo/source.bin" --plan "$privateWork/patch-demo/verified-plan.json" --output "$privateWork/patch-preview"
python -B binary_patch_planner.py --source "$privateWork/patch-demo/source.bin" --plan "$privateWork/patch-demo/verified-plan.json" --output "$privateWork/patch-applied-report" --apply-output "$privateWork/patch-candidate.bin"
python -B binary_patch_planner.py --source "$privateWork/patch-demo/source.bin" --plan "$privateWork/patch-demo/unexpected-plan.json" --output "$privateWork/patch-review"
```

Linux shell, after setting `private_work` to your existing absolute private directory:

```sh
python3 --version
python3 -B examples/generate.py --output "$private_work/patch-demo"
python3 -B binary_patch_planner.py --source "$private_work/patch-demo/source.bin" --plan "$private_work/patch-demo/verified-plan.json" --output "$private_work/patch-preview"
python3 -B binary_patch_planner.py --source "$private_work/patch-demo/source.bin" --plan "$private_work/patch-demo/verified-plan.json" --output "$private_work/patch-applied-report" --apply-output "$private_work/patch-candidate.bin"
```

Use `python3` wherever that is your Python 3.12+ command. The generator creates
four invented files, including a 16-byte source. The verified plan has two edits
covering six declared bytes; its candidate is the fictional text
`ORCHARD-TEST-v2` followed by LF. Preview exits **0**, creates only report files
and leaves the source intact. Explicit application exits **0** and creates the
separate 16-byte candidate plus a different report directory. The unexpected-byte
example exits **1** and has no candidate to apply. The overlap example exits
**2** before a normal report is created. Nonzero example exits are intentional.

Read [examples](examples/README.md) and [the exact plan/report format](docs/FORMAT.md)
before selecting real inputs.

## Your own plan

```text
python -B binary_patch_planner.py --source ABSOLUTE_FILE --plan ABSOLUTE_PLAN_JSON --output NEW_ABSOLUTE_REPORT_DIRECTORY
```

Add `--apply-output NEW_ABSOLUTE_FILE` only when you want a separate candidate.
The report and candidate parents must already exist, and the destinations must
be distinct and outside each other. No input, report directory, candidate file
or existing hardlink/symlink is overwritten. File paths and ancestors must be
local, absolute and free of links/reparse points. UNC/device paths, Windows
alternate streams and ambiguous/reserved Windows destination names are refused.
Use stable trusted files and parents you control.

Plan schema version 1 has exactly `schema_version`, `source` and `patches`:

```json
{
  "schema_version": 1,
  "source": {"bytes": 16, "sha256": "LOWERCASE_64_DIGIT_SOURCE_SHA256"},
  "patches": [
    {"offset": 8, "expected_hex": "44454d4f", "replacement_hex": "54455354"}
  ]
}
```

The hash placeholder above must be replaced with the source's actual SHA-256.
Use the generator's complete valid plan for a runnable example. Do not use a
hash supplied by an untrusted source as an independent authenticity check.
Offsets are zero-based decimal integers. Hex values are contiguous pairs of
hexadecimal digits, without `0x`, whitespace, wildcards or expressions. Each
replacement must have exactly the expected byte length. Order does not matter;
adjacent edits are supported, overlap/repeated ranges are rejected. A no-op
replacement is permitted and reported as `changes_bytes: false`.

The input is a physical regular file, not an archive or mounted image to be
interpreted. The tool does not decompress/repack, insert/delete bytes, update
format checksums or signatures, resolve inherited game properties, execute a
candidate or modify a running application. Supply only plans/files you have
rights to inspect and change; input rights do not transfer to this repository.

## Reports, receipt and exit codes

Each completed inspection writes `report.json`, escaped static `report.html`
and `MANIFEST.json`. Open the HTML locally or consume JSON. There is no script,
active input content or remote resource. The manifest covers **only JSON/HTML**,
not the optional separately selected candidate file.

For an applied candidate, `application` records `created`, `verified`, byte
length and SHA-256. That is the candidate's separate receipt. It omits its local
filename; you must retain the explicit command/path mapping privately. The
candidate SHA must match `candidate_sha256`. A preview has a candidate hash
only if all source/byte checks pass, and `created: false`. If source checks fail,
an explicit application request is recorded but withheld. It creates no candidate.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | The preview passed the selected checks; an explicit application also completed readback verification. |
| 1 | `REVIEW_REQUIRED` | Source hash/size or expected bytes disagree; no candidate is applied. |
| 2 | `INCOMPLETE` | Invalid arguments/plan/path, a resource limit, changing input or I/O failure prevented completion. |

Stdout contains fixed status/count/error fields, never filenames or patch bytes.
Reports contain sizes, source/plan hashes, offsets, expected-byte match flags,
candidate hashes and application receipt fields. They omit raw source,
expected/replacement bytes and local paths. **This is not anonymization**: hashes,
offsets and lengths can identify a source or proprietary edit. Plans contain the
byte payloads and are private unless separately reviewed for publication.

The report destination is checked before application. File creation is exclusive;
there is no in-place mode, automatic overwrite or cleanup of failed artifacts.
If application or subsequent report writing fails, a new partial or even verified
candidate file may remain while the command exits 2. A partial report directory
can also remain. Retain/review those files privately and choose new destinations
for a retry. The operation is **not transactional across candidate and report**.
File flush/readback checks are not proof of power-loss durability or an atomic
filesystem snapshot. Files changed after a read snapshot may not be detected.

## Limits and validation

The source and applied readback are each limited to **4 MiB**. The plan is at
most **1 MiB**, with **1–1,000** edits, at most **4,096 bytes/edit** and **1 MiB**
of declared edit bytes total. JSON/text overhead can make the plan byte limit
bind sooner. JSON has at most 40,000 nodes, depth 8 and 8,192 characters/string;
duplicate keys, non-integer numeric literals, nonfinite constants, unsupported
controls, extra fields and implicit conversions are refused. Each report is at
most **8 MiB**. Bounds fail explicitly rather than silently truncating a plan.

Run from this module folder:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

Tests use generated bytes, strict/malformed plans, exact candidate outputs,
path/alias refusals, actual CLI calls and simulated write/readback/report failures.
Shared first-party safeguards are copied for standalone use. Platform/link
creation skips remain separate from passes. See [validation](docs/VALIDATION.md).

Read [provenance](docs/PROVENANCE.md), [security](SECURITY.md) and
[contribution guidance](CONTRIBUTING.md). Suggestions and fictional bug examples
are welcome through the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach game assets, firmware, proprietary patch recipes, credentials,
private captures, real binaries or identifying reports.
