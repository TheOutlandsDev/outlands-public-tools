# Using the order workbook preflight inspector

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-workbook-preflight-inspector-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, run the fictional example with Python 3.12.16 or 3.15.2. The inspector has no third-party runtime dependencies.

~~~text
python -B examples/make_workbook.py fictional.xlsx
python -B workbook_preflight.py fictional.xlsx
~~~

The example reports two external workbook references and two worksheet error tokens. The counts report omits reference paths and cell values. The generator creates a new file and refuses to overwrite an existing file.

External link count is the larger of the external link XML part count and the number of distinct workbook references found in relationships or formulas. The error count reports literal occurrences of #REF!, #DIV/0!, #VALUE!, #NAME?, #NUM!, and #NULL! in worksheet XML, including occurrences in text. These are diagnostic counts from the supplied workbook.

The CLI requires an ordinary file with standard XLSX package parts. It rejects macro-enabled types, VBA projects and macro sheets, unsafe or duplicate member names, encrypted or unsupported members, and XML document type or entity declarations in inspected parts. Limits are 25 MiB per input, 2,000 ZIP members, 200 MiB total uncompressed and 16 MiB per inspected XML part. Invalid input returns exit code 2. A readable workbook produces a JSON counts report with exit code 0, including when findings are present.
