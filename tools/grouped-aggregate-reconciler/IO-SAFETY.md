# Input and output safety

Input is a bounded JSON file selected by the caller. Decoding rejects duplicate keys, floating point literals, excessive size/depth, and malformed scalar types. `--out` uses the copied checked-file helper to write a new file outside source under a trusted existing parent. No existing file is overwritten. Reports may include supplied row IDs, group keys, and aggregate values; do not publish reports made from private input. Hashes do not anonymize input. No database, SQL engine, browser, provider, network, or target update is used.
