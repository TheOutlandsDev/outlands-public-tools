# Offline Route Selection and Detail Reporter

Extract the source ZIP and open a terminal in the extracted directory. The CLI uses the Python standard library. Use Python 3.12 or 3.15. In the commands below, replace `python` with `python3` if that is your interpreter name.

```text
python route_detail.py examples/contract.json examples/snapshot.json
python route_detail.py examples/contract.json examples/snapshot.json --flow "Paint Shop" --version 1
```

The first command selects `Assembly Lab` version `2` and reports three ordered occurrences, including two separate `Inspect` steps with the same step ID. The second selects `Paint Shop` version `1` and reports one occurrence. The default is the first route in flow-name and version order. Supply both flags for an explicit, case-sensitive selection.

`contract.json` declares expected counts for each flow and version under `routes`. The snapshot has `total_occurrences`, `summaries`, and `occurrences`. Every summary uses the string fields `requested_flow_name` and `requested_version` and an integer `occurrence_count`. Occurrence rows add `route_order_key` (starting with `R:`), integer `step_position`, `step_name`, `step_id` (starting with `ID:`), and `step_correlation_id` (starting with `CID:`). See the examples for the full shape.

The report checks the summary population against the contract and the selected route's detail count against its summary. Detail rows are ordered by route-order key, step position, and correlation ID. Output includes the declared route summaries and selected steps. The CLI reads the two UTF-8 JSON files and prints JSON to standard output. Invalid input prints a diagnostic to standard error and exits with code 2. Each input is limited to 8 MiB, 20 routes, and 1,000 total occurrences.

Compare the downloaded ZIP against `SHA256SUMS.txt` using `Get-FileHash -Algorithm SHA256` in PowerShell or `sha256sum` on Ubuntu. The release's `VALIDATION.json` records the four operating system and interpreter profiles.
