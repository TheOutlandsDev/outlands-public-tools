# Filesystem Permission Manifest Diff

Compare declared Android-style filesystem metadata by literal path: numeric
UID/GID, octal mode and optional SELinux label/capability mask. Review supported
changes while holding duplicates and unsupported identities conservatively.
Python 3.12 or newer, standard library only, original [MIT source](LICENSE).

Declared paths are metadata keys and are never opened. The tool never changes
permissions/ownership, evaluates SELinux policy, applies capabilities or verifies
effective access. It does not access devices or use real permission manifests
in qualification. A declared difference is not an automatic security verdict.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/permission-manifest-diff-v0.1.0),
including ZIP, checksums, usage guide, public validation JSON and build manifest.
Verify hashes before extracting into a new owned directory. The ZIP contains
thirty reviewed source files plus their manifest, 31 members; Python, actual
manifests, target-files/binaries, generated reports and raw logs are excluded.
No pip package, administrator rights, Android SDK, SELinux utility or device is
required. Keep `permission_diff.py`, `declaration_diff.py` and
`inspection_support.py` adjacent with the rest of the module.

The [executable guide](USAGE.md) creates fictional before/after sets and checks
normalization, all supported field changes, null-versus-zero, literal labels,
ambiguity/uncertainty holds, privacy modes and refusals. It independently verifies
input/report hashes and unchanged files. Use an existing absolute private
directory outside source; every fixture/report destination must be fresh.
Never apply the invented metadata to a filesystem or device.

From this module folder, after setting your existing private work directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/permission-demo"
python -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/same.txt" --output "$privateWork/permission-same-report"
python -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/changed.txt" --output "$privateWork/permission-changed-report" --include-details
python -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/review.txt" --output "$privateWork/permission-review-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/permission-demo"
python3 -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/same.txt" --output "$privateWork/permission-same-report"
python3 -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/changed.txt" --output "$privateWork/permission-changed-report" --include-details
python3 -E -s -B permission_diff.py --before "$privateWork/permission-demo/before.txt" --after "$privateWork/permission-demo/review.txt" --output "$privateWork/permission-review-report"
```

Same exits 0 despite numeric spelling, declaration order and option-order changes.
Changed intentionally exits 1 for declared UID/mode/capability changes. Review
exits 1 with one known path held for unsupported fields and another held for
duplicates, without arbitrary pairing or invented removal. Repeat `--before`
and `--after` for selected sets, up to 32 files total. Read local static HTML/JSON.

## Literal paths, numbers and optional fields

```text
python -E -s -B permission_diff.py --before ABSOLUTE_BEFORE --after ABSOLUTE_AFTER --output NEW_ABSOLUTE_DIRECTORY
```

Rows are `relative/path UID GID OCTAL_MODE`, followed by optional
`selabel=CONTEXT` and `capabilities=0xHEX` at most once each. ASCII spaces/tabs
delimit fields. Blank/full-line `#` comments are ignored; inline comments,
quoting and escapes are unsupported. Paths are at most 512 characters using
the documented forward-slash ASCII subset without empty/dot/parent components.
They compare exactly and case-sensitively, without lookup, case folding or
filesystem normalization. See [FORMAT.md](docs/FORMAT.md).

UID/GID are 1–10 decimal digits representing 0–4294967295. Leading zeroes
normalize numerically. Mode is 1–4 octal digits normalized to four digits
0000–7777. Symbolic modes, usernames and file-type-bit modes such as 100644 are
unsupported. Capability masks require lowercase `0x` plus 1–16 hex digits and
normalize to lowercase hex strings, preserving full uint64 values in JSON.
Missing optional values remain null/unspecified, distinct from explicit zero
or a label. Contexts are bounded literal user:role:type:level/category text;
category order is text, not an evaluated SELinux set.

Unique supported paths compare UID, GID, mode, label and capabilities. Unknown,
repeated or invalid fields hold the entire known path as unsupported, preserving
its identity without inventing removal. Duplicate paths on either side/across
files stay held with every record ID, even if identical; no first/last winner
or arbitrary pairing is chosen. Indexes combine selected files without precedence.

Unsupported path syntax produces unidentified-row coverage. Unmatched identities
are held when their opposite side has unidentified paths because absence cannot
be assessed within selected parsed scope. Unique matched supported changes
remain visible alongside coverage. Case/path renames become removal/addition
only where supported selected absence can be assessed. Empty/comment manifests
can exit 0 for limited empty scope, not completeness.

No chmod/chown, ownership lookup, SELinux/access check, label/capability application,
target-files archive, binary config, actual target path or device operation occurs.
Effective access, deployment correctness, bootability, source rights and security
risk assessment are outside scope. A mode/mask change is a declared difference.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`, with SHA-256/byte lengths for both report payloads. Each selected
before/after file has a separate exact-byte hash/size record. Unsigned hashes
establish consistency, not authentic authorship, ownership, access or deployment
safety. HTML has no scripts or external resources. Stdout uses fixed codes/counts.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported finding/coverage issue; selected scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Changes, ambiguous/unsupported identities or coverage needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, budgets or I/O prevented completion. |

Defaults omit declared paths/values and local filenames while retaining opaque
record IDs, sides/source-line locations, supported flags, field-change labels,
counts, hashes and hold/coverage reasons. Details add declared identities and
supported normalized fields; known unsupported paths have an identity but no
invented fields. Raw lines/unknown metadata/local filenames remain omitted.
IDs are report-local and follow input order. Omission is not anonymization:
hashes/structure/details can identify inputs. Keep actual manifests/reports
private; see [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, budgets and failure limits

Select distinct stable regular local manifest files with absolute paths.
Duplicate/hardlink identities across both sides, links/reparse routes, traversal,
UNC/device paths and Windows alternate streams are refused. These checks apply
to selected input/output paths; declared metadata target paths are never opened.
Inputs and earlier reports are not replaced. Use an existing owned parent and
new output directory. Failed writes may leave a partial new folder: preserve it,
fix the cause and choose a different fresh destination.

Budgets are 32 selected files, 1 MiB each, 4 MiB aggregate; 20,000 split physical
lines including final empty line; 8,192 characters/line; 4,000 rows per bounded
collection; and 8 MiB each for JSON/HTML. Strict UTF-8 accepts optional BOM and
LF/CRLF. Invalid encoding, bare CR/NUL and unsupported controls are refused.
Bounds fail incomplete rather than silently truncate. No Event-JSON or XML
input format is implemented here.

Stable-input/cooperative checks are not an OS sandbox, atomic snapshot against
hostile mutation, hard I/O deadline, rollback transaction or durable-output
guarantee. No system scan, subprocess/shell, network, permission/ownership/policy
change or device action occurs in the inspector. Tests/guide launch only this
Python code on disposable authored manifests.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving 39 original
methods and adding thirty copied-runtime methods. Eight lanes select 552 methods;
actual passes and finite native skips stay separate in release validation.
Fresh environments have no pip and zero installed distributions. Original
runtime, generator, tests and four historical docs remain unchanged. The shared
comparison helper is included locally for standalone imports. The unchanged
[historical validation](docs/VALIDATION.md) is a distinct earlier record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional bug/suggestion reproductions are
welcome via the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach real manifests, customer data, credentials or unredacted reports.
Inspected inputs retain their owners' rights/licenses.
