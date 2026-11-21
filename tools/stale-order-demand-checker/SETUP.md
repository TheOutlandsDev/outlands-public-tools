# Run the Offline Stale Order Demand Checker

Download the source ZIP and its SHA-256 file. Verify the ZIP from the download directory.

Windows PowerShell:

```powershell
Get-FileHash .\stale-order-demand-checker-0.1.0.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

Ubuntu:

```bash
sha256sum -c SHA256SUMS.txt
```

Extract the ZIP and open a terminal in the extracted folder. The CLI uses the Python standard library. Run the fictional example with Python 3.12 or 3.15.

```text
python stale_order_demand.py examples/orders.json
```

On Ubuntu, use python3 if that is the name of the selected interpreter. The example reports {"stale_order_ids": ["stale-open"]}. Supply a JSON object with an active_order_ids array and a states object keyed by order ID. Each state requires a boolean cancelled field and an integer remaining_quantity field. IDs match exactly, and duplicate JSON keys are rejected.

An order is flagged when its ID is absent from active_order_ids, it is uncancelled, and its remaining quantity is positive. IDs appear in sorted order. The CLI exits with status 0 for an empty result, 1 when stale orders are found, and 2 for invalid input. It reads the supplied snapshot without querying a database.

The release validation records cover Windows and Ubuntu with Python 3.12.16 and 3.15.2 using fresh source ZIP extractions.
