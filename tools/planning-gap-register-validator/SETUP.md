# Offline Planning Gap Register Validator

Extract the source ZIP and open a terminal in the extracted directory. Use Python 3.12 or 3.15. On Ubuntu, use `python3` if `python` is unavailable. The CLI uses only the Python standard library.

```text
python planning_gap_register.py examples/gap-register.csv
```

The fictional example reports 19 products. Eight have confirmed lot quantities and still need timing review. Eleven need business inputs and carry reference-only lot quantities. A passing report confirms that the CSV satisfies the draft register contract. The report's `importable` field is always false.

Use the example's exact header order for your own saved register. The input must be UTF-8 CSV, with or without a UTF-8 BOM. Keep the `PRODUCT_GAP_REGISTER_ONLY` role and `NOT_IMPORTABLE_MODEL_EVOLUTION_REQUIRED` status. Record IDs and canonical part numbers must be unique, ignoring case.

For `TIMING_REVIEW_PENDING`, supply a positive confirmed lot quantity and a positive reference-only lead-time candidate. For `FAIL_CLOSED_BUSINESS_INPUT_REQUIRED`, leave the approved lot quantity and timing candidate blank. A legacy lot quantity can be supplied as a reference. Business-review and technical-validation fields must stay in their draft states with blank evidence.

The CLI reads a local file and writes JSON to standard output. Malformed or out-of-contract input exits with code 2 and sends a diagnostic to standard error. Inputs are limited to 1 MiB and 2,000 product rows. The report includes canonical part numbers grouped by state. It omits reviewer fields, remarks, aliases, and quantity values.

Compare the ZIP against `SHA256SUMS.txt` using `Get-FileHash -Algorithm SHA256` in PowerShell or `sha256sum` on Ubuntu. See `VALIDATION.json` for the Windows and Ubuntu qualification records.
