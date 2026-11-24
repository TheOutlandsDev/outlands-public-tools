# Run the Offline WIP Search and Filter Validator

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\wip-search-filter-validator-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. The validator uses Python's standard library.

Windows PowerShell

```powershell
python wip_search_filter.py examples/fictional-filter.json
```

Ubuntu

```bash
python3 wip_search_filter.py examples/fictional-filter.json
```

The fictional request selects VIEW-A, VIEW-B, and VIEW-E in configured order. It reports DEMO-LOT-001 as the search, page 1, and a page size of 50.

## Request format

Save the request as UTF-8 JSON up to 1 MiB. Use the example as a starting point.

| Field | Value |
| --- | --- |
| products | Nonempty array of objects with canonical_modality and display_modality |
| modalities | Optional array of aliases, with comma-separated values allowed in each string |
| search | Optional literal search text |
| page | Optional integer from 1 through 1,000. Defaults to 1. |
| page_size | Optional integer from 1 through 100. Defaults to 50. |

Each declared alias starts with an uppercase letter or digit and may also contain underscores or hyphens. The request can use either alias for a product. Requested aliases are trimmed and matched case-insensitively. Selecting a product through both aliases still produces one row in the order of the products array. Omitted, null, or blank selections use all configured products.

The validator trims outer whitespace in the search string. An empty result becomes JSON null. Literal search text may contain up to 80 characters after trimming. Control characters remaining after trimming cause validation to fail.

The command prints selected_products, search, page, and page_size to standard output and leaves the saved request intact. A valid request exits 0. Invalid input exits 2.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
