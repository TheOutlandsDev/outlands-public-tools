# Suggestions and contributions

Use the collection's ELF Inspector bug or suggestion form. Describe your use
case, OS, Python version, tool commit/version, expected result and a tiny original
or generated reproduction. Improvements to format coverage, report navigation,
diagnostic clarity and accessibility are welcome. Suggestions are welcome;
response times are not guaranteed.

Do not attach proprietary software/firmware, private sysroot reports, keys, phone
identifiers or real data. Explain why you have rights to any contributed fixture.
Prefer additions to the original metadata generator over binary fixture files.
Never add inspected-binary execution to runtime code or tests.

Run source_check.py and unittest discovery from README. For reviewed source
changes, update the explicit allowlist when necessary and regenerate the manifest
with `python -B source_check.py --write-manifest`. Generation is not provenance or
privacy approval. Preserve MIT notices; document any new dependency and its terms.
