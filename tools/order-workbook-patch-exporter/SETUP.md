# Run the Offline Order Workbook Patch Exporter

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\order-workbook-patch-exporter-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. The exporter uses Python's standard library. The fictional example creates a small workbook and its matching saved orders in a new directory.

Windows PowerShell

```powershell
python examples/make_demo_workbook.py demo
python order_workbook_patch.py demo/template.xlsx demo/orders.json demo/patched.xlsx
```

Ubuntu

```bash
python3 examples/make_demo_workbook.py demo
python3 order_workbook_patch.py demo/template.xlsx demo/orders.json demo/patched.xlsx
```

The output workbook has quantity 120 in F4, the literal text " =DEMO " in D4, the commit date serial in I4, and a cleared planning note in U4. A4 retains its formula. Unedited worksheet parts retain their original bytes. On an edited sheet, the declared used range expands to include new cells. The CLI prints the number of patched rows and the output workbook's SHA-256.

## Saved order snapshot

Use demo/orders.json as a template. Set source_sha256 to the lowercase SHA-256 of the template and source_row_count to the number of entries in orders. Each entry contains source_sheet (C or P), source_row (4 through 500), and a nonempty fields object. Each sheet and row pair may appear once. record_origin defaults to SOURCE_IMPORT. Use MANUAL to enable the additional fields below.

| Fields | Columns |
| --- | --- |
| purchase_order, po_line, quantity | D, E, F |
| commit_date, ship_quantity, ship_date | I, J, K |
| dock_date, lot_ids, lot_quantities, work_request_flow | N, O, P, Q |
| customer_notes, planning_notes | T, U |
| order_date, part_number, requested_ship_date, organization (manual) | B, C, G, H |
| shipment_number, checked_by, carrier, tracking_number (manual) | L, M, R, S |

Omit a field to leave its cell alone. Use JSON null to clear a value. Supply dates as YYYY-MM-DD on or after 1900-03-01. Dates are written as Excel serial numbers. Use preformatted date cells in the template to display them as dates. Quantities are integers, with a positive quantity and a nonnegative ship_quantity. Other field values are plain text, including text that begins with an equals sign.

Use an XLSX template with C and P worksheets under xl/worksheets and the 1900 date system. The tool refuses macro packages, unsafe or duplicate ZIP paths, XML document type declarations and formulas in targeted cells. Limits are 2 MiB for the JSON snapshot and 32 MiB for the XLSX template, with up to 512 ZIP entries and 64 MiB of uncompressed package content.

Choose a new output filename in an existing directory. On Ubuntu, use a destination filesystem that supports hard links. Successful export exits 0. A validation or output error exits 2. The exporter stages a complete copy before publishing and leaves both inputs in place.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
