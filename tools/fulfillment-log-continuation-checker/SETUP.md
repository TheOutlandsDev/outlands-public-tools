# Offline Fulfillment Log Continuation Checker

Extract the source ZIP and open a terminal in the extracted folder. Use Python 3.12 or 3.15. On Ubuntu, use `python3` if `python` is unavailable. The checker uses only the Python standard library.

```text
python fulfillment_log_check.py examples/fulfillment.txt examples/allocations.json
```

The fictional example passes with 32 order groups and 33 recognized allocation lines. The first order has a continuation from `DEMO-LOT-01-A` at K6 to `DEMO-LOT-01-B` at K5. Swap these two allocations in a copy of the report to see an `ORDERED_LOTS_DIFFER` issue.

The log uses lines such as `For Week #17 Index #1-DEMO-PART-A we need -->300 -->DEMO-LOT-01-A @ Kanban #6`. The parser recognizes this header and collects each lot marker in the order it appears. It skips other lines, groups consecutive recognized rows for each order key, and takes demand from the first line in each group. A repeated key in a later group is ambiguous and fails validation.

The allocation JSON has an `orders` array. Each order needs `week`, `index`, `part_number`, and an `allocations` array whose rows supply `lot_id` and numeric `kanban`. The checker matches orders by key. Within each matched order it compares the exact sequence of lot IDs and Kanban numbers.

Both inputs accept UTF-8 with an optional BOM and are limited to 4 MiB each. The CLI reads the files and prints JSON to standard output. It exits 0 for a match and 1 for a comparison with differences. An unreadable or invalid input exits 2 with a diagnostic on standard error.

Compare the ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for the four qualification profiles.
