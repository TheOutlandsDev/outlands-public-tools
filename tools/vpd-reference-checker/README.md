# OUTLANDS | VPD Media Reference Checker

Inventory path references in a supported **VideoProc Vlogger `.vpd` JSON
structural subset**, then optionally check explicitly mapped local copies before
moving a project. This original [MIT tool](LICENSE) uses Python 3.12/3.13 and the
standard library. No editor, FFmpeg, third-party packages or network service is
required.

The tool reads the selected project document and optional mapping JSON. It never
opens a media body, plays a clip, follows an embedded project path, launches an
editor, changes a project, or relinks references. Its optional availability check
uses filesystem metadata only. A regular file can be empty, corrupt, unrelated
to a reference, or otherwise unusable; this tool does not establish media integrity.

VideoProc's [official project guide](https://www.videoproc.com/video-editing-software/guide-free-win/create-new-project.htm)
identifies `.vpd` projects and describes its own archive workflow. It does not
publish the JSON schema implemented here. Our initial subset comes from observed
structures in owner-held records; **editor/version compatibility is unverified**.
Other VPD formats and other editors are unsupported.

## Try a generated example

Clone [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools),
open a terminal in `tools/vpd-reference-checker`, and run `python --version`.
Follow the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md). In the
PowerShell commands below, set `$privateWork` to an existing absolute private
directory outside the repository. Every destination must be new.

```powershell
python -B vpd_references.py --help
python -B examples/make_demo.py --destination "$privateWork/vpd-demo" --complete
python -B vpd_references.py --project "$privateWork/vpd-demo/project.vpd" --output "$privateWork/vpd-inventory"
python -B vpd_references.py --project "$privateWork/vpd-demo/project.vpd" --mapping "$privateWork/vpd-demo/mapping.json" --media-root "$privateWork/vpd-demo/copies" --output "$privateWork/vpd-mapped-report"
```

The fixture is invented structural JSON, not an editor-validated project. Its
two `.mp4` files are **empty placeholders**, not playable recordings. The first
inspection exits **0** with `INVENTORY_ONLY`: three references are recorded,
including the project-record path, and none is followed. The mapped inspection
exits **0** with `NO_MAPPING_FINDINGS`: two explicit mapped paths exist as regular
files. This result does not mean the placeholders are valid media.

Open the generated `report.html` locally for a readable table, or read
`report.json`. Both reports omit embedded path text by default. `MANIFEST.json`
records their exact lengths and SHA-256 hashes. A missing or mismatched report
invalidates that report set; hashes are not signatures or ownership evidence.

The same Python commands work on Linux after replacing the variable with your
chosen absolute paths. See [the walkthrough](examples/README.md) for the missing
file example, expected nonzero exits and report verification.

## Inspect your own project

1. Stop the editor or use a stable copy of one `.vpd` file. Choose a new report
   directory in your private workspace. The parent directory must already exist.
2. Run the inventory-only command with that absolute project path. The tool
   requires `projinfo.projectfile`, `timeline.subitems` and four media-bin
   `subitems` lists. Unsupported structural shapes fail visibly.
3. Review the reference IDs, roles and coverage issues in `report.json`.
   Known bin positions are path **candidates**, not proof a file is used on the
   timeline. The project-record path and unclassified `path` fields are kept
   separate and cannot be mapped as media.
4. If you want availability observations, create a mapping bound to the exact
   `project_sha256` from that report. Map the desired reference IDs to portable
   relative paths under one explicitly selected local copy directory. Supply
   both `--mapping` and `--media-root`, with a new output directory.

Example mapping shape:

```json
{
  "schemaVersion": 1,
  "projectSha256": "REPLACE_WITH_64_HEX_CHARACTERS_FROM_THE_PROJECT_REPORT",
  "files": [
    {"referenceId": "ref-000002", "relativePath": "media/clip-a.mp4"}
  ]
}
```

Replace both the hash and reference ID with values from your own report; IDs in
the fictional example are not universal. A changed project requires a new
inventory/mapping. The chosen relative copy is an operator assertion: an
existing regular file does not prove it corresponds to the original reference.
Embedded absolute, network, URL and traversal-like strings are never used as
filesystem lookup paths, even when a media root is supplied.

Only explicit mapped relative paths are checked. Traversal, drive/device paths,
backslashes, reserved names, unsafe components, links and reparse points are
rejected. Case/NFC collisions in different mapping spellings fail. Multiple
references may explicitly map to the same exact relative path; their shared
copy ID and reuse counts are reported, rather than counted as distinct copies.
Unmapped media candidates remain uninspected and require review.

## Results and coverage

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `INVENTORY_ONLY` | The documented structural inventory completed; no mapped availability check was requested. |
| 0 | `NO_MAPPING_FINDINGS` | All supported media-bin references were mapped and observed as regular files, with no documented coverage issue. This is a metadata result. |
| 1 | `REVIEW_REQUIRED` | A mapped path was missing, linked, nonregular or unavailable; a media candidate was unmapped; or supported coverage was incomplete. |
| 2 | `INCOMPLETE` | Invalid/unsupported input, exceeded limit, stale or invalid mapping, I/O failure, or output failure. No completed report set is claimed. |

`metadata_unavailable` is distinct from `missing`. Counts describe array entries,
references and metadata check attempts; they are not verified clip, render or
playback counts. JSON outside the supported roles is not a complete semantic
project interpretation. Unknown path fields, bin entries lacking a string path,
and uncounted timeline shapes become coverage issues. Read the
[format reference](docs/FORMAT.md) for exact roles, bounds and statuses.

Project input is capped at **8 MiB**, mapping input at **1 MiB**, nesting at
**32**, JSON values at **100,000**, strings at **65,536 characters**, references
and mappings at **5,000**, and each generated report at **16 MiB**. Limits are
fixed in this initial version; a larger/unsupported project must not be treated
as successfully inventoried by increasing or removing a guard locally.

## Privacy and filesystem assumptions

Default reports omit project input filenames, local root paths, embedded path
text, titles and unknown JSON pointer text. They still contain the project hash,
sizes, structural locations and counts, which may identify work. Add
`--include-path-text` only to deliberately include original embedded paths and
full JSON pointers in private reports. It can reveal users, shares, URLs and
other identifying text. HTML is escaped, static, contains no scripts/external
assets, and supplies no links that open referenced files.

Keep actual projects, mappings, reports, recordings, `.userdata`, credentials and
editor assets outside public source exports. Omission is not a general-purpose
anonymizer or secret scanner. No reading or reporting grants redistribution
rights over a project, media or software.

Use trusted, quiescent regular local files and parent directories. Existing
symlinks/reparse points are refused and regular inputs are checked before and
after bounded reads; metadata observations are sequential, not an atomic view
of a whole project. A malicious concurrent filesystem writer can race path
checks. Native filesystem calls have no universal timing bound. Output uses a
fresh directory and exclusive files; a failed write may leave a new partial
directory. Existing outputs and project/media inputs are not overwritten.

## Tests and suggestions

```text
python -B -m unittest discover -s tests -v
python -B source_check.py
```

Tests use authored JSON, synthetic filesystem entries and empty placeholders;
no real project, editor or recording is used. See the [validation record](docs/VALIDATION.md)
and [provenance](docs/PROVENANCE.md). Source manifests check reviewed source
bytes, not application compatibility or input ownership.

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=vpd_reference_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=vpd_reference_suggestion.yml).
Suggestions for clearer reports or additional documented shapes are welcome.
Provide a tiny fictional reproduction and your Python/OS/source version; do not
attach real projects, media, identifying mappings or unredacted reports.
See [CONTRIBUTING.md](CONTRIBUTING.md).
