# Source provenance

This standalone download is derived from `tools/verified-transfers` in [TheOutlandsDev/outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools). Its reviewed baseline is collection revision `ef68892d3f48d52f97708ae6e8ccaa4472542929`. The release build manifest records the exact committed source revision and finite member hashes; release VALIDATION.json identifies the actual qualified source and archive.

The original suite selects 39 transfer methods from the shared transfer/maintenance source: fourteen source-package, five manifest-validation and twenty data-handoff methods. All six supporting shared nodes are copied byte-exactly. The 55 additional I/O methods comprise 27 portable, ten POSIX and eighteen Windows cases. Maintenance bodies and runtimes are excluded. Preservation checks retain 130 assertion calls (125 in tests and five in helpers) and sixteen supporting helpers. Native support enforces applicable platform capabilities around the preserved bodies, with fixture/import checks.

`transfer_windows.py`, historical `IO-SAFETY.md` and original regression bodies are preserved against the baseline. `transfer.py` has one source-directory boundary repair at its header: the literal `tools/verified-transfers` layout retains the collection root, while a flat standalone copy protects its own runtime directory. Transfer functions/classes, bundle formats, parsing rules and native I/O implementation are unchanged. This is structural layout recognition, not arbitrary Git-root discovery.

New standalone source includes copied-runtime CLI tests, native test support, packaging/qualification helpers, a source inventory and explanatory documents. The license is copied exactly from the collection root. The source gate excludes unselected collection tools, interpreters, dependencies, operational records, private receipts and raw logs.

The guide authors its own tiny fictional inventory in the accepted schema. It does not ship or run Public Release Audit, and no generated inventory is treated as publication approval. Private probes, failed controls and detailed receipts remain separate from this generic source release.
