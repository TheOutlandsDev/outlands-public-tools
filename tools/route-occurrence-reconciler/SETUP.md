# Run the Offline Route Occurrence Reconciler

Download the source ZIP and SHA256SUMS.txt. In the download folder, compare the Windows PowerShell output of Get-FileHash .\route-occurrence-reconciler-0.1.0.zip -Algorithm SHA256 with SHA256SUMS.txt. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP, open a terminal in the extracted folder, and run the fictional example with Python 3.12 or 3.15:

```text
python route_occurrence.py examples/demo_routes.csv examples/metadata.json examples/empty-inventory.json
```

Use python3 on Ubuntu if that selects the intended interpreter. The CLI needs only the Python standard library. The example reports 239 missing occurrences across five route versions.

The CSV must use the 22 headers shown in the example. Its metadata declares the filename, CSV SHA-256, row count and source workbook SHA-256. Build the saved inventory from an independent snapshot of the route records you want to reconcile. Supply a matching source_workbook_sha256 and an occurrences array. Each entry contains route_occurrence_key and source_row_sha256. The key joins RequestedFlowName, RequestedVersion and RouteOrderKey with a vertical bar. The row hash is SHA-256 of the original cell strings in header order, joined by the ASCII unit separator and encoded as UTF-8.

The output gives expected, matched and missing totals, counts per flow and version, and the source CSV row number and hash of each missing occurrence. Row 1 is the header. Repeated step IDs at different route positions are separate occurrences.

The CLI reads only the three supplied files. It returns 0 for a complete match, 1 for missing occurrences, and 2 for invalid input, a changed hash or an unexpected occurrence. The validation records cover Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
