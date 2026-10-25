# Validation and evidence boundaries

Run `python -B -W error -m unittest discover -s tests -v` and
`python -B source_check.py` from this module folder. VINTF exercises its original restricted XML reader;
no native XML parser is required or imported by its inspector.

Local suites use CPython 3.12.14 on Windows (VINTF also CPython 3.12.7) with disposable fictional files. The
CI matrix runs all three source gates and suites on Ubuntu Python 3.12/3.13 and
Windows Python 3.13/3.14, with warnings treated as errors. These are generated
metadata tests, not real disk/device/runtime acceptance.

Shared tests cover source immutability, duplicate/linked input refusal, byte and
line limits, fresh output, HTML escaping and SHA-256 report manifests. Specific
suites exercise GPT CRC/range corruption, module graph ambiguity/cycles and
VINTF declaration comparison, restricted XML grammar and unsupported syntax, including actual Python CLI
subprocesses and generated examples. No native helper or network is invoked.
The GPT suite also uses a large logical sparse-file fixture on POSIX to verify small bounded reads; it does not allocate or hash a multi-gigabyte payload.

Windows alternate-stream syntax tests run only on Windows. POSIX FIFO and sparse
file tests run where supported. Link-creation tests skip when the environment
cannot create the required link. Skips are recorded separately from passes.
The local restricted filesystem lacks some link capabilities; CI covers those
mechanisms where available. Read the Actions result for the source commit.

The unsigned source manifest uses an explicit source-only allowlist. It verifies
bytes and catches accidental drift, not authenticity, rights or universal secret
absence. Parser/graph/CRC results remain limited to the documented subset.
