# Offline Query Result CSV Comparator

Compare two local CSV exports with the original RDL Query Lab comparator. It
aligns columns by name or a complete one-to-one mapping, compares field values
as exact strings, and counts duplicates. Row and column order can differ. The
JSON report contains counts and optional SHA-256 row fingerprints.

Use the [setup and usage guide](SETUP.md) with the included fictional CSVs or
download the [source ZIP and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/query-result-csv-comparator-v0.1.0).

The comparator, package marker and seven original `unittest` cases are preserved
byte for byte. `ORIGINAL-SHA256.json` pins those three files. The release adds
fictional inputs, a packaging recipe and copied-CLI checks. The test matrix
uses Python 3.12.16 and 3.15.2 on Windows and Ubuntu. The runtime uses only the
Python standard library and reads saved files locally.
