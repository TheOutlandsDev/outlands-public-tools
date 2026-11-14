# Windows Event Timeline Inspector

Build a chronological report from explicitly selected saved event metadata.
Group provider/channel/event-ID/version declarations, observe declared time gaps
and review repeated/conflicting exported record IDs. Python 3.12 or newer,
standard library only, original [MIT source](LICENSE).

The tool never queries live event logs, decodes native EVTX/EVT binaries or
uses a native XML parser. It reads saved normalized JSON or its own restricted
XML subset without opening external resources. Computers and raw event payloads
are never serialized, even with details. Observations do not prove complete
logs, authentic host identity, downtime or a failure's cause.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/windows-event-timeline-v0.1.0),
including ZIP, checksums, usage guide, public validation JSON and build manifest.
Verify hashes before extracting into a new owned directory. The ZIP contains
32 reviewed source files plus their manifest, 33 members; Python, real logs,
event binaries, generated reports and raw logs are excluded. No pip package,
administrator rights, native XML library or Windows log access is needed.
Keep the module intact, including `restricted_xml.py` and `inspection_support.py`.

The [executable guide](USAGE.md) creates fictional saved JSON/XML, checks exact
timeline/group/identity/gap observations and privacy modes, independently verifies
input/report hashes and exercises controlled refusals. Choose an existing
absolute private directory outside source; fixture/report destinations must be
new. The retained [manual export guide](docs/EXPORTING.md) is separate from
qualification: no real log query or export command is run by these checks.

From this module folder, after setting your existing private work directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/event-demo"
python -E -s -B event_timeline.py --file "$privateWork/event-demo/clean.json" --format json --output "$privateWork/event-json-report"
python -E -s -B event_timeline.py --file "$privateWork/event-demo/clean.xml" --format xml --output "$privateWork/event-xml-report" --include-details
python -E -s -B event_timeline.py --file "$privateWork/event-demo/review.json" --format json --output "$privateWork/event-review-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/event-demo"
python3 -E -s -B event_timeline.py --file "$privateWork/event-demo/clean.json" --format json --output "$privateWork/event-json-report"
python3 -E -s -B event_timeline.py --file "$privateWork/event-demo/clean.xml" --format xml --output "$privateWork/event-xml-report" --include-details
python3 -E -s -B event_timeline.py --file "$privateWork/event-demo/review.json" --format json --output "$privateWork/event-review-report"
```

Clean JSON/XML exit 0 with the same three accepted events and two groups.
Repetition is an observation, not automatically a finding. Review intentionally
exits 1 for a duplicate, declared gap and naive timestamp coverage. Read static
local HTML or JSON; real event messages are not needed for this walkthrough.

## Explicit format, exact time and identity scope

```text
python -E -s -B event_timeline.py --file ABSOLUTE_SAVED_EXPORT --format json --output NEW_ABSOLUTE_DIRECTORY
```

Choose `--format json` or `xml`; repeat `--file` to combine selected files of that
format. Native event binaries are unsupported. Normalized JSON requires the
documented schema, rejects duplicate keys/floats/NaN and has its own structure
budgets. It does not inherit XML's physical line-length cap. The original bounded
XML reader has no Expat/ElementTree/SAX dependency. It supports the documented
Event/Events subset, unnamespaced or using the supported Windows default
namespace. Arbitrary prefixes, namespace resets and invalid metadata require
coverage. DTD/entity declarations, CDATA, malformed trees/references and reader
bounds fail the whole run. No URI, include, schema or external entity is followed.

Timestamps need Z or a known explicit offset, with one to seven fractional
digits. Exact integer arithmetic retains 100 ns precision; no float/local-zone
guessing occurs. Unknown -00:00, naive/invalid dates, leap seconds and unsupported
precision require review. Canonical UTC detail strings retain seven fractional
digits. Elapsed/delta/gap ticks and detailed record IDs are decimal strings so
JSON consumers can preserve large integers. Equal ticks retain input order,
without establishing causality. See the exact [format contract](docs/FORMAT.md).

Groups use exact provider, normalized optional GUID, channel, event ID, optional
version and qualifiers. Missing values are not zero. Accepted duplicates remain
in counts/timeline. Record-ID comparison requires declared computer, channel
and record ID, scoped to one selected input file. Equal inspected fields give a
duplicate; differing inspected fields give a conflict. Cross-file deduplication,
actual host identity, omitted-payload equality and complete capture are not inferred.

`--gap-seconds` defaults to 300; only strictly greater adjacent sorted intervals
produce gap findings. Zero disables gaps; the maximum is 31,536,000. Mixing
selected files/computers does not verify clock accuracy or loss-free coverage.
A gap or repeated event is not proof of downtime, failure or its cause.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json` with SHA-256/byte lengths for both report payloads. Each selected
input has a separate exact-byte hash/size record. Unsigned hashes establish
consistency, not author authenticity, host identity, completeness or rights.
HTML has no scripts or external resources. Stdout uses fixed statuses/counts/errors.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported finding/coverage issue; selected scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Scoped identity/gap findings or incomplete metadata coverage. |
| 2 | `INCOMPLETE` | Arguments, input/parser/budget refusal or I/O prevented completion. |

Defaults retain relative intervals, event IDs, levels, opaque group IDs, input
roles/record positions, counts and hashes. `--include-details` adds canonical UTC,
provider/GUID/channel and record IDs. Computer names are used only internally
for identity scope and are always omitted. Raw messages, event payload/security
data, unknown field values and local input filenames remain omitted in both
modes. JSON array/XML Event-child positions are not source line numbers. IDs
depend on input order. Omission is not anonymization: hashes/structure and
accepted details can identify inputs. Keep actual captures/reports private;
review details before sharing. See [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Stable inputs, bounds and failure limits

Inputs must be distinct stable regular local files with absolute paths. Duplicate
identities/hardlinks, links/reparse routes, traversal, UNC/device paths and Windows
alternate streams are refused. Inputs are read-only; only fresh report files
are created. Use an existing owned output parent and new directory. Earlier
reports are not replaced. Failed writes can leave a partial new folder: preserve
it, fix the cause and choose another new output.

Budgets are 32 selected files, 1 MiB each, 4 MiB aggregate, 4,000 accepted events
and bounded report rows, and 8 MiB each for JSON/HTML. JSON caps depth at eight,
structure nodes at 40,000, keys at 256 and strings at 8,192 characters; control
strings/floats/nonstandard numbers are refused. XML text supports optional BOM,
LF/CRLF, 20,000 split physical lines including final empty line and 8,192
characters/line. Reader limits include 8,000 elements/file, depth 32, sixteen
attributes, names 256, attribute values 1,024 and text/tail nodes 8,192.

The Event reader deliberately permits encoded CR in XML text, while identity
validators reject controls in identifying metadata. Discarded payload text is
not serialized. Bare physical CR/NUL and unsupported text controls are refused.
Do not substitute a sibling tool's reader/helper. Bounds fail incomplete rather
than silently truncate. Checks are not an OS sandbox, atomic snapshot against
hostile mutation, hard I/O deadline or durable-output guarantee. No system scan,
log query, shell/subprocess, network, device action or permission/config change
occurs in the inspector. Tests/guide launch only this Python code on fictional files.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving 59 original
methods and adding thirty copied-runtime methods. Eight lanes select 712 cases;
actual passes and finite native skips stay separate in release validation.
Fresh environments have no pip/installed distributions. The original Event
reader/helper are unchanged; no native XML dependency or Expat pin is introduced.
The unchanged [historical validation](docs/VALIDATION.md) remains a separate record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional bug/suggestion reproductions are
welcome via the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach real logs/configs, customer data, credentials or unredacted reports.
Inspected inputs retain their own ownership and licenses.
