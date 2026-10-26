# Validation and limits

Run from the module directory with Python 3.12 or newer:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

The reviewed Windows/CPython 3.12.7 run discovered 61 methods: 58 passed
and 3 platform/environment skips, with no failures/errors. These counts include
the standalone copy of shared guard tests. Windows hardlink/symlink creation
was unavailable in the restricted environment, and POSIX FIFO behavior is a
platform-only case. CI provides independent Windows/Linux runs; skips remain
separate from passes. The repository review records final batch results.

Fixtures exercise supported quoting and limits, exact large version strings,
literal leading zeros, SDK codenames and absence, package identity changes,
duplicate package/attribute/SDK/library rows, required/optional changes,
common-library relative order, unknown opposite-side holds for both SDK fields
and libraries, known unsupported library identities, ignored payload omission,
combined issue collection limits, UTF-8/BOM/CRLF/control limits and metadata
privacy. Actual CLI subprocess tests verify exit codes, input preservation,
fresh output refusal, fixed errors, escaped HTML and report manifests.

All inputs are temporary generated text. No proprietary APK, vendor firmware,
real manifest report, live AAPT2 capture, binary Android XML, emulator, device,
app install, signing or compatibility test is included. The inspector itself
does not import subprocess or launch an external tool. The tests launch only
this module's own Python CLI (and fictional generator where covered).

Shared file safeguards reject unsupported paths and detect sampled concurrent
changes; they do not provide a hostile same-user filesystem transaction or
protection against every undetectable in-place change. Unsigned source/report
manifests prove neither origin nor completeness. A clean subset comparison is
not app safety, a complete manifest diff or effective runtime equivalence.
