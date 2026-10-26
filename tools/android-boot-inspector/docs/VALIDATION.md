# Validation and limits

Run from this module with Python 3.12 or newer:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

The suite uses generated temporary files only. It covers hand-checked v3/v4
boot and vendor section offsets, signature placement, multi-page vendor headers,
zero-size declarations, exact metadata reads and selected vendor table extents.
Malformed fixtures exercise short headers, unknown magic/versions, reserved
words, header sizes, page-size coverage, component/padding truncation, trailing
bytes, large declarations, table product/count/stride issues, fragment
out-of-range/overlap/gap/type handling, empty tables and metadata budgets.

CLI fixtures invoke the actual Python entry point and check all three exit
classes, fixed output codes, fresh JSON/HTML/manifest creation, exact report
hashes and refusal to overwrite. The example generator is exercised on a fresh
directory. Shared first-party support tests cover regular files, path guards,
changing snapshots, text/JSON limits, fresh report escaping and manifests. Those
shared tests appear in each standalone module and do not represent additional
distinct product features.

Local Windows checks discover 53 methods. Platform skips are reported separately:
POSIX FIFO requires POSIX, Windows alternate-stream syntax is Windows-only, and
link creation can be unavailable in restricted test environments. Use the
reviewed CI evidence for actual Windows/Ubuntu outcomes; unsupported local link
creation is not counted as a pass. A restricted environment may need its `TEMP`
and `TMP` environment variables pointed at an existing writable private folder.

No actual firmware, APKs, physical devices, live partitions, extraction tools,
Android SDK, bootloader or deployment commands are used. Generated files are
deliberately non-bootable. These tests do not establish real hardware support,
Android compatibility, firmware safety, authenticity, signature validity,
bootability or AVB integrity. The inspector's declared layout observations may
help an investigation but do not replace upstream verification or a device test.

The source gate uses an explicit UTF-8 source-only allowlist, parses Python files
and compares SHA-256 inventory entries. It detects changes against the reviewed
manifest, not malicious authorship or every possible private value. The manifest
is unsigned; verify a trusted commit separately when provenance matters.
