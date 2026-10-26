# Offline Session Telemetry Analyzer

Summarize selected **saved JSONL telemetry** without launching a game, watching
processes or querying live logs. The report counts supported event types,
population samples, line-of-sight booleans, tracking observations, malformed
records and declared dropped data. Python **3.12 or newer**, standard library
only, original [MIT source](LICENSE).

The public implementation generalizes a personal telemetry-summary helper. It
contains no game/plugin implementation, actual capture, device configuration,
game installation path or dependency on SPT. See [provenance](docs/PROVENANCE.md).

## Install and try fictional examples

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/session-telemetry-analyzer`. Run `python --version`; no package
installation, administrator privileges, game, device or network service is
required. Use `python3` if that is your Python 3.12+ command.

Choose an existing absolute private work directory outside the source checkout.
Keep real inputs and reports there. Each generated/report directory must be new.
See the collection's [private workspace guide](../../docs/PRIVATE-WORKSPACE.md).

Windows PowerShell, after setting `$privateWork` to that existing directory:

```powershell
python -B examples/generate.py --output "$privateWork/telemetry-demo"
python -B telemetry_analyzer.py --file "$privateWork/telemetry-demo/clean.jsonl" --output "$privateWork/telemetry-clean-report"
python -B telemetry_analyzer.py --file "$privateWork/telemetry-demo/review.jsonl" --output "$privateWork/telemetry-review-report"
python -B telemetry_analyzer.py --file "$privateWork/telemetry-demo/missing-fields.jsonl" --output "$privateWork/telemetry-missing-report"
```

Linux shell, after setting `private_work` to that existing directory:

```sh
python3 -B examples/generate.py --output "$private_work/telemetry-demo"
python3 -B telemetry_analyzer.py --file "$private_work/telemetry-demo/clean.jsonl" --output "$private_work/telemetry-clean-report"
python3 -B telemetry_analyzer.py --file "$private_work/telemetry-demo/review.jsonl" --output "$private_work/telemetry-review-report"
python3 -B telemetry_analyzer.py --file "$private_work/telemetry-demo/missing-fields.jsonl" --output "$private_work/telemetry-missing-report"
```

| Input | Exit | Expected result |
| --- | --- | --- |
| `clean.jsonl` | 0 | Six accepted events, three snapshots. Player mean `6/2`, bot mean `12/2`, tracked-active mean `4/2`, visible fraction `1/2`, one end declaration with zero dropped lines. |
| `review.jsonl` | 1 | Invalid player/tracking samples, one malformed JSON record and multiple end rows. The dropped-line value is held rather than summed. |
| `missing-fields.jsonl` | 0 | Two snapshots, but only one valid player sample: zero. The player mean is `0/1`; absent bot/tracking samples have null means. |

Nonzero review-example exits are intentional. Open each local `report.html` or
consume `report.json`. The report's exact mean is a numerator/denominator object;
the fraction notation above is for readability. Run each example with a fresh
output directory. The generator refuses existing destinations.

## Inspect selected saved files

```text
python -B telemetry_analyzer.py --file ABSOLUTE_LOCAL_CAPTURE --output NEW_ABSOLUTE_DIRECTORY
python -B telemetry_analyzer.py --file ABSOLUTE_CAPTURE_A --file ABSOLUTE_CAPTURE_B --output ANOTHER_NEW_DIRECTORY
```

Every file is summarized **separately**. The tool does not identify or segment
sessions, infer which files belong together, deduplicate copied records or pool
players/bots across captures. Repeated observations contribute repeatedly. A
filename is not evidence of one unique session; multiple start/end markers are
explicit review items. No files are discovered or collected automatically.

The supported envelope is a JSON object with `type` and object-valued `payload`.
Recognized types are `raid_start`, `snapshot`, `tracking_assigned` and `raid_end`.
Snapshot population counts and line-of-sight fields are optional. Unsupported
rows or fields receive fixed coverage codes, while uniquely understood valid
samples remain visible. The [format contract](docs/FORMAT.md) defines every
supported field, bound, blank-line/BOM extension and incomplete-input behavior.
This is a deliberately narrow saved-report reader, not a parser for every
producer version or a general JSON Lines validator.

## What the statistics mean

- Each population has its **own valid-present sample denominator**. A missing,
  malformed or invalid field is not replaced by zero. Zero is valid when
  explicitly declared. A mean with no valid samples is null.
- Means weight each accepted sample equally. They are not time-weighted averages,
  unique entity counts, concurrent-player proofs or rates. A sum of player
  observations is not a count of different players.
- Line-of-sight booleans describe the supplied observations only. Missing values,
  invalid entries and invalid collections are counted separately. No visibility
  probability, AI quality, game performance or causal diagnosis is inferred.
- `raid_seconds` is an optional nonnegative number preserved exactly as a
  decimal string in the last accepted declaration. It is not an authenticated
  clock or measured session duration. A decrease is a review observation.
- A single valid end declaration can report dropped lines. Multiple supported
  end rows make that value ambiguous, even when their values match; they are
  never summed or given a first/last winner. No end/dropped field means
  unspecified, not zero or lossless recording.
- No supported events, malformed JSON, unknown fields/types, invalid selected
  metrics, declared dropped data and ambiguous markers require review. A clean
  result does not prove complete capture, correct game state or a healthy system.

## Reports, privacy and exit codes

Successful report creation produces exactly `report.json`, escaped static
`report.html` and `MANIFEST.json` with the reports' SHA-256 hashes and byte lengths.
HTML has no scripts, remote resources or active input content. Manifests are
unsigned consistency checks; they do not prove authorship or authenticity.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | Supported selected observations produced no finding or coverage issue. |
| 1 | `REVIEW_REQUIRED` | Findings, invalid records/samples, unsupported coverage or ambiguity remain explicit. |
| 2 | `INCOMPLETE` | Invalid path/encoding, argument, resource bound, changing file, I/O or output failure prevented a complete result. |

The analyzer opens explicit stable regular inputs read-only and creates fresh
report files. Relative paths, parent traversal, network/device routes, Windows
alternate streams, symlinks/reparse paths and duplicate same-file/hardlink inputs
are refused. The report parent must already exist. Existing output is refused;
an I/O failure can leave a partial fresh directory, so use a new name for a retry.
Stable-input checks are not an atomic snapshot or a hostile-filesystem sandbox.

Local source filenames, map names, player/bot identifiers and raw payloads are
never emitted. Coverage includes fixed codes, opaque source IDs, physical line
numbers and static field labels. Stdout contains fixed status/count/error fields.
There is no details mode that reveals raw records. **Omission is not anonymization**:
capture hashes, sizes, sample counts, exact declared times and structure can
identify a source. Review all output privately before sharing.

## Bounds, tests and suggestions

Limits: 32 files, 1 MiB/file, 4 MiB aggregate, 4,000 nonblank records across all
selected files, 20,000 split physical lines/file including the terminal empty
split element before normalization, 8,192 characters/line, JSON depth eight,
1,000 JSON value nodes/record, 256 line-of-sight entries/snapshot, 4,000 rows per
bounded finding/report collection and 8 MiB each for JSON/HTML output. Detailed
numeric and string limits are in [FORMAT.md](docs/FORMAT.md). Bounds fail with
exit 2 rather than silently truncating a report.

Run from the module directory:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

Tests use fictional inputs and the actual authored Python CLI. Read
[validation](docs/VALIDATION.md), [security boundaries](SECURITY.md) and
[contribution guidance](CONTRIBUTING.md). Shared helper tests are repeated to
support standalone downloads, not counted as separate application features.

Bug reports, usability ideas and supported-format proposals are welcome through
the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's bug or suggestion form, provide the commit/OS/Python version,
and include a small invented reproduction. Keep real telemetry, credentials,
game files, identifiers and unredacted reports out of public issues.
