# Android Sparse Image Inspector

Review the structure of one local Android sparse image before using another
tool to reconstruct it. The inspector checks file and chunk boundaries,
declared output sizes and recognized chunk accounting. It reads **metadata
headers only**, skips payload bytes, and never reconstructs, extracts, mounts,
flashes or executes an image.

Original [MIT source](LICENSE), Python **3.12 or newer**, standard library only.
There is no Android SDK, AOSP binary, third-party Python package or network
dependency. A regular file is required; physical drives and device paths are
outside scope.

## Quick start with generated examples

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools).
Run commands from `tools/android-sparse-inspector`. First choose an existing
absolute private work directory outside the source checkout. Each output folder
must be new. Do not upload actual firmware or identifying reports to an issue.

Windows PowerShell, after setting `$privateWork` to that existing directory:

```powershell
python --version
python -B .\examples\generate.py --output "$privateWork\sparse-demo"
python -B .\sparse_inspector.py --image "$privateWork\sparse-demo\valid.sparse" --output "$privateWork\sparse-valid-report"
python -B .\sparse_inspector.py --image "$privateWork\sparse-demo\crc-unverified.sparse" --output "$privateWork\sparse-crc-report"
python -B .\sparse_inspector.py --image "$privateWork\sparse-demo\truncated.sparse" --output "$privateWork\sparse-truncated-report"
```

Linux, after setting `privateWork` to that existing directory:

```sh
python3 --version
python3 -B examples/generate.py --output "$privateWork/sparse-demo"
python3 -B sparse_inspector.py --image "$privateWork/sparse-demo/valid.sparse" --output "$privateWork/sparse-valid-report"
python3 -B sparse_inspector.py --image "$privateWork/sparse-demo/crc-unverified.sparse" --output "$privateWork/sparse-crc-report"
python3 -B sparse_inspector.py --image "$privateWork/sparse-demo/truncated.sparse" --output "$privateWork/sparse-truncated-report"
```

The generator creates three tiny, invented binary fixtures in your private work
directory. It refuses an existing destination. Expected results:

| Input | Exit | Expected observation |
| --- | --- | --- |
| `valid.sparse` | 0 | Three RAW/FILL/DONT_CARE chunks account for 4 blocks, 16 declared output bytes. The inspector reads 64 metadata bytes. |
| `crc-unverified.sparse` | 1 | Four chunks; `CRC32_UNVERIFIED` coverage remains explicit because no payload checksum is calculated. |
| `truncated.sparse` | 1 | The final chunk header is truncated; the layout walk stops with `CHUNK_HEADER_TRUNCATED`. |

Open `report.html` locally or inspect `report.json`. Reports describe selected
metadata, never a successful firmware recovery or deployment. A nonzero exit in
these last two examples is intentional. Use a different fresh output folder on
each run.

## Inspect a file you are allowed to inspect

```text
python -B sparse_inspector.py --image ABSOLUTE_LOCAL_IMAGE --output NEW_ABSOLUTE_REPORT_DIRECTORY
```

The input must be a stable regular file in directories you control. Relative
paths, parent traversal, linked/reparse routes, Windows alternate data streams,
UNC paths and device routes are rejected. One image file is inspected per run.
The tool does **not** combine numbered `sparsechunk` files or infer their order.
Each part can have its own structural report; that does not establish that parts
form a complete or compatible reconstruction set.

Supported base layout: Android sparse major version 1 with at least a 28-byte
file header and 12-byte chunk headers, positive block size divisible by four,
and RAW, FILL, DONT_CARE and CRC32 chunk types. New minor versions and larger
header sizes retain explicit coverage issues; their extra fields are not
interpreted. An unsupported major version or unknown chunk type stops the walk.
Read [the exact supported format](docs/FORMAT.md) before interpreting results.

## Output and exit codes

Each successful report-writing run creates exactly:

- `report.json`: structured header/chunk observations, findings, coverage and
  selected metadata-region hashes.
- `report.html`: escaped, static local rendering of the same JSON; no scripts,
  external resources or active image contents.
- `MANIFEST.json`: SHA-256 and byte counts for those two report files. This is
  unsigned consistency evidence, not authenticity evidence.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | Recognized metadata passed the implemented checks with no coverage issues. |
| 1 | `REVIEW_REQUIRED` | A structural finding or explicit coverage limitation was recorded. A partial structural walk may still have a report. |
| 2 | `INCOMPLETE` | Invalid arguments, path/I/O changes, limits or report creation prevented a normal result. A report is not promised. |

Stdout contains fixed status/count/error fields, never the source filename or raw
payload. Reports omit local paths and payload bytes, but **are not anonymized**:
sizes, layouts and metadata-region hashes can correlate an image. Review reports
privately before sharing. File-region hashes cover only the bytes actually read;
the entire image is not hashed, and CRC declarations are not checked.

## Bounds and limitations

The selected input and declared expanded image are each limited to **16 TiB**.
Block size is at most **1 MiB**; chunk count is at most **4,000**. At most **1 MiB**
of metadata can be read, and each JSON/HTML report is limited to **8 MiB**. The
base-header walk normally reads `28 + 12 * inspected_chunks` bytes. It seeks over
RAW/FILL/CRC payloads and extension bytes rather than allocating declared output
sizes. Resource limits produce exit 2, not a pass.

No payload CRC, filesystem contents, Android Verified Boot signature, partition
selection, reconstructed image, sparsechunk-set completeness, device compatibility
or bootability is validated. DONT_CARE means a declared skipped output range;
the report does not claim actual destination bytes are zero or erased.
`layout_walk_complete` means the declared chunk sequence was walked, not that
every check passed. Stable-file checks detect ordinary changes during reading;
they do not make an atomic filesystem snapshot or resist a malicious concurrent
writer with control of the filesystem.

## Tests and contributions

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

Tests use original generated files, including malformed headers, resource
declarations, output accounting, reader changes and actual CLI invocations. See
[validation](docs/VALIDATION.md), [provenance](docs/PROVENANCE.md) and
[security boundaries](SECURITY.md). Shared safeguard tests are repeated so the
module remains standalone; they are not separate application features.

Suggestions, bug reports and supported-format proposals are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Include the source commit, OS/Python version and a small **invented** reproduction.
Please read [CONTRIBUTING.md](CONTRIBUTING.md) before sharing inputs.
