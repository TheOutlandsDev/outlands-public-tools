# Android VINTF Manifest Inspector

Index supported HAL instance declarations in explicitly selected Android VINTF
XML, optionally comparing current and before file sets. Review duplicate/conflicting
declarations and added, removed or changed supported instances. Python 3.12 or
newer, standard library only, original [MIT source](LICENSE).

An included first-party bounded XML-subset reader handles this documented
grammar without Expat, ElementTree, SAX or another native XML-parser dependency.
The tool never opens external resources, merges effective device configuration,
applies overrides, evaluates a compatibility matrix or contacts runtime HALs.
Selected declarations are not device compatibility, service presence or boot proof.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/vintf-manifest-inspector-v0.1.0),
including source ZIP, checksums, usage guide, public validation JSON and build
manifest. Verify hashes before extracting into a new owned directory. The ZIP
contains 31 reviewed source files plus their manifest, 32 members; Python,
actual device manifests, binaries, generated reports and raw logs are excluded.
No pip package, administrator rights, Android SDK, native XML library, device
or service connection is required. Keep the module intact, including
`restricted_xml.py` and `inspection_support.py`.

The [executable guide](USAGE.md) creates fictional XML, indexes and compares
selected fragments, verifies explicit expected declarations/changes/ambiguity,
checks privacy modes/input/report hashes and exercises parser/file refusals.
Use an existing absolute private directory outside the source folder. Every
fixture/report destination must be new; never deploy these invented manifests.

From this module folder, after setting your existing private work directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/vintf-demo"
python -E -s -B vintf_inspector.py --file "$privateWork/vintf-demo/clean.xml" --output "$privateWork/vintf-index-report"
python -E -s -B vintf_inspector.py --before "$privateWork/vintf-demo/clean.xml" --file "$privateWork/vintf-demo/same.xml" --output "$privateWork/vintf-same-report"
python -E -s -B vintf_inspector.py --before "$privateWork/vintf-demo/clean.xml" --file "$privateWork/vintf-demo/changed.xml" --output "$privateWork/vintf-changed-report" --include-details
python -E -s -B vintf_inspector.py --file "$privateWork/vintf-demo/review.xml" --output "$privateWork/vintf-review-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/vintf-demo"
python3 -E -s -B vintf_inspector.py --file "$privateWork/vintf-demo/clean.xml" --output "$privateWork/vintf-index-report"
python3 -E -s -B vintf_inspector.py --before "$privateWork/vintf-demo/clean.xml" --file "$privateWork/vintf-demo/same.xml" --output "$privateWork/vintf-same-report"
python3 -E -s -B vintf_inspector.py --before "$privateWork/vintf-demo/clean.xml" --file "$privateWork/vintf-demo/changed.xml" --output "$privateWork/vintf-changed-report" --include-details
python3 -E -s -B vintf_inspector.py --file "$privateWork/vintf-demo/review.xml" --output "$privateWork/vintf-review-report"
```

Index and equivalent declaration forms exit 0. Changed and review examples
intentionally exit 1. Repeat `--file` for current fragments and `--before` for
prior fragments, at most 32 selected files total. Read static local HTML/JSON.

## Restricted XML and selected instance scope

```text
python -E -s -B vintf_inspector.py --file ABSOLUTE_CURRENT_XML --output NEW_ABSOLUTE_DIRECTORY
```

The original XML reader supports balanced ASCII element/attribute names,
quoted attributes, comments, XML 1.0 declarations and bounded predefined/numeric
references decoded once. It is not a general-purpose XML implementation.
DTD/entity declarations, CDATA, unhandled markup, malformed references and
malformed trees are refused. DTD/entity markers are conservatively refused
even in comments. No include, XInclude, URI, schema or external resource is
resolved. Namespace declarations/prefixed names require coverage without
interpreting that file's HALs. Processing instructions are coverage, not executed.

Supported manifest metadata is version 1.0/2.0 and device/framework type, with a
documented HIDL/AIDL subset. HIDL supports explicit interface/version and fqname
forms; fqname has its own version. AIDL requires meta-version 2.0 and exactly
one explicit integer version in this subset. Defaults from platform context
are not inferred. Unknown transport/architecture data remains coverage and is
not copied as normalized transport/arch fields. See [FORMAT.md](docs/FORMAT.md).

Comparison identity includes manifest type, HAL format, package, version,
interface and instance. Supported equivalent forms compare equally; a version,
instance or type change is removal/addition. For unique matching identities,
supported transport/architecture changes produce changed records. Duplicate
identities on either side are held as ambiguous; no first/last winner or
arbitrary pairing is chosen. Selected fragments are indexed together without
effective merging. Device/framework declarations remain distinct identities.

Root target-level and other non-instance changes are outside instance-diff
scope. Overrides, level/APEX modifiers, unknown grammar/elements and mixed text
remain explicit coverage. Supported partial observations can coexist with
coverage; additions/removals do not prove presence/absence in a full effective
configuration. An empty valid manifest can exit 0 for an empty selected scope;
empty bytes or malformed XML are refused.

This does not replace `assemble_vintf`, `checkvintf`, full XML/schema validation,
fragment/override merging, API-level selection or framework compatibility-matrix
checking. Native HALs, unselected manifests and runtime service availability
are outside scope. No Android build tool, device or service is invoked.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`, which hashes/length-checks both report payloads. Each selected
before/current file has a separate exact-byte input hash/size record. Unsigned
hashes establish consistency, not author authenticity, ownership, service
availability, effective configuration or compatibility. HTML has no scripts or
external resources. Stdout uses fixed status/count/error fields, not local paths.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported finding/coverage issue; selected scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Differences, ambiguity, selected findings or coverage needs review. |
| 2 | `INCOMPLETE` | Arguments, refused input, XML/bounds or I/O prevented a complete result. |

Defaults omit package/version/interface/instance/transport details and local
filenames, retaining opaque IDs, source roles, element ordinals, format/type,
change labels, counts and hashes. `--include-details` adds only supported
normalized declaration fields. Raw XML, comments, unknown scalar values and
local filenames remain omitted. Element ordinals are preorder positions excluding
comments, not source lines; IDs depend on selected input/declaration order.
Omission is not anonymization: hashes/structure can identify input. Keep actual
manifests and identifying reports private and review details before sharing.
See [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, budgets and failure limits

Select distinct stable regular local files with absolute paths. Duplicate-file
and hardlink aliases across all current/before roles, links/reparse routes,
traversal, UNC/device paths and Windows alternate streams are refused. Input
files are read-only. Strict UTF-8 supports optional BOM and LF/CRLF; unsupported
controls/bare CR/encoding are refused.

Budgets are 32 files total, 1 MiB each, 4 MiB aggregate; 20,000 split physical
lines including a final empty line and 8,192 characters/line. Per-file reader
limits are 8,000 elements, depth 32, 16 attributes/element, 256-character
attribute names, 1,024-character attribute values and 8,192-character text/tail
nodes. Common collections cap at 4,000 rows; JSON/HTML each at 8 MiB. Bounds
fail incomplete rather than silently truncate. See the exact format contract.

Use an existing owned parent and fresh report directory. Inputs and earlier
reports are not replaced. A failed write can leave a partial new folder; retain
and review it, fix the cause and select another new output. These checks are
not an OS sandbox or atomic snapshot against hostile concurrent mutation.
No recursive scan, network, shell/subprocess, privileged operation, configuration
edit or device access occurs in the inspector. Tests/guide launch only this
Python code on disposable authored fixtures.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving all 58
original methods and adding thirty copied-runtime methods. Eight lanes select
704 methods; actual passes and finite native skips remain separate in release
validation. Fresh application environments have no pip and zero installed
distributions. The original restricted reader is unchanged; no native XML
dependency or Expat pin is introduced. The unchanged
[historical validation](docs/VALIDATION.md) remains a distinct earlier record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional bug/suggestion reproductions are
welcome via the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not submit actual manifests/firmware, credentials, customer data, device
identifiers, binaries or unredacted reports. Inspected inputs retain their rights.
