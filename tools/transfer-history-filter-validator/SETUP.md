# Run the Offline Transfer History Filter Validator

Download the source ZIP and verify its SHA-256 against the release checksum. Run these commands from the folder containing both files.

PowerShell:

```powershell
Get-FileHash .\transfer-history-filter-validator-0.1.0.zip -Algorithm SHA256
```

Ubuntu:

```bash
sha256sum -c SHA256SUMS.txt
```

Extract the ZIP and open a terminal in the extracted folder. Use Python 3.12 or 3.15. The CLI has no third-party runtime dependencies. Run the fictional example on Windows with:

```powershell
python transfer_history_filters.py examples/filters.json --products examples/products.json
```

On Ubuntu, use the same command with `python3`. The JSON result contains the year, page, page size and selected display aliases. The example selects LUMEN01 and ORBIT02 in product-list order. The repeated LUMEN selection appears once.

The request accepts years 2020-2100, pages 1-1000, and page sizes 1-100. Omit the modality list, use null or supply an empty list to select every approved product. The list can contain canonical aliases, display aliases, or comma-separated selections. Matching ignores case and surrounding whitespace. Unknown aliases exit with status 2 and a diagnostic on stderr.

Use the product-list example as the shape for a caller-supplied approved list. Supply one canonical and one display alias per product. Both must use uppercase spellings. The CLI reads the two JSON inputs and emits normalized filters without running a history query.

The validation record documents fresh extracted-ZIP runs on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
