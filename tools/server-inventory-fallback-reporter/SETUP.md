# Run the Offline Server Inventory Fallback Reporter

Download the source ZIP and `SHA256SUMS.txt`. Compare the ZIP's SHA-256 with `Get-FileHash .\server-inventory-fallback-reporter-0.1.0.zip -Algorithm SHA256` on Windows, or run `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal there. The CLI uses the standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python server_inventory_fallback.py examples/replay-fallback.json
```

Ubuntu

```sh
python3 server_inventory_fallback.py examples/replay-fallback.json
```

The example reports a stale inventory, keeps the previous fictional server and summary, and calculates a cached age of 75 seconds from the original capture time. The saved system source remains fresh.

Supply an ISO timestamp as `generated`, a nonnegative `duration_ms`, and exactly one `inventory.result` or `inventory.error`. A result supplies a `programs` array and `summary` object. An error supplies a type and message. An invalid result uses the same fallback as a collection error. Optionally include the `previous` snapshot and `source_health` for current independent sources. Use the example for the field names.

An available cached list and summary are retained unless their prior source is marked unavailable. The report calculates age against the supplied replay timestamp, preferring the previous source's capture time and falling back to the previous snapshot time. A fresh result uses the replay timestamp as its capture time. An unusable cache yields an empty list and summary.

The JSON report can be passed directly to the [Offline Telemetry Source Freshness Classifier](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/telemetry-source-freshness-classifier). The replay reads one UTF-8 JSON file up to 1 MiB, writes to stdout, and makes no live collection calls. Invalid input returns exit status 2. The report can retain saved server metadata and up to 500 characters of the error label and message.
