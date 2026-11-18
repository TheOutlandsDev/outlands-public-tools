# Use the Offline NVIDIA Telemetry Output Parser

## Verify and extract the download

Download the source ZIP and its SHA-256 checksum from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/nvidia-telemetry-output-parser-v0.1.0).
Compare the SHA-256 printed by your shell with the entry for the ZIP. Use the
ZIP as the source if the hashes match.

In Windows PowerShell, run

```powershell
Get-FileHash .\nvidia-telemetry-output-parser-0.1.0.zip -Algorithm SHA256
Expand-Archive .\nvidia-telemetry-output-parser-0.1.0.zip .\nvidia-parser
Set-Location .\nvidia-parser
```

In Ubuntu, run

```bash
sha256sum nvidia-telemetry-output-parser-0.1.0.zip
unzip nvidia-telemetry-output-parser-0.1.0.zip -d nvidia-parser
cd nvidia-parser
```

Change to the directory containing `SETUP.md` if your extractor creates a
top-level folder. Use Python 3.12 or 3.15. On Ubuntu substitute `python3` for
`python` if that is the command for your interpreter.

## Run the fictional example

```text
python -B -m sentinel_monitor --csv examples/query.csv --replay examples/replay.txt
```

The JSON has a `readings` array and a human-readable `status`. The example
reports GPU 0 with 7 replays and GPU 1 with 0 replays. The second GPU's
temperature is unknown and appears as `null`. The malformed sample row is
skipped. Omit `--replay` when only the CSV is available. The replay field is
then `null` for every reading.

## Supply saved output

Use a UTF-8 file, with or without a BOM, up to 4 MiB per input. The GPU CSV
uses the `csv,noheader,nounits` format and the following 19 columns in order.

```text
index,uuid,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit,fan.speed,pstate,clocks.current.graphics,clocks.current.memory,serial,pci.bus_id,driver_version,driver_model.current,driver_model.pending
```

The optional replay text contains `Bus Id` and `Replays Since Reset`
lines such as those in `examples/replay.txt`. PCI bus matching ignores
letter case. Rows with an unexpected column count or invalid GPU index
are skipped. Missing numeric values appear as `null`, as do non-finite
numbers in JSON. Unreadable or incorrectly encoded inputs and files or CSV fields that exceed
size limits produce an error and exit status 2.

The CLI parses saved data and emits JSON to stdout. A report includes the
identifiers in the input, including GPU UUIDs, serials and PCI bus IDs.
Use the fictional examples when sharing output publicly. The separately
exposed `NvidiaCollector` class retains the original live collection
path for callers that deliberately instantiate and invoke it.

## Verify the source

Run `python -I -B source_check.py` from the extracted directory to
check the source manifest. Runtime use needs only the Python standard
library. To run the tests in an isolated Python environment, install
the pinned test dependencies with
`python -m pip install --require-hashes -r requirements-test.txt`, then run
`python -B -m pytest -q -p no:cacheprovider`.

The release includes qualification records for Windows and Ubuntu with
Python 3.12.16 and 3.15.2. Those checks rebuild and extract the source
archive, run the preserved cases and the new API cases, then exercise
the CLI on saved fictional inputs.
