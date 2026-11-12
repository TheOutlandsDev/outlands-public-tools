# Standalone qualification contract

This qualification targets Windows x64 and Ubuntu x86_64 on CPython 3.12, 3.13,
3.14 and 3.15.2. Actual patches, method IDs, skip reasons, artifact hashes and
executed dependency versions belong to the release's `VALIDATION.json`.
Required checks are described here without treating future or skipped cases
as passes.

## Preserved source and selected methods

The two runtime files, original 27 regression methods and 45 portable/native
methods are retained from reviewed collection main. The selected runtime and
original test/helper bodies are verified against that baseline. See
[provenance](PROVENANCE.md). The fictional Markdown input remains unchanged.
Any test loading/native capability policy surrounds the preserved methods;
it must not relax a body, assertion or application check.

Thirty additional `test_download.Download` methods copy only the runtime pair
to a new private directory and invoke the current interpreter in fresh
processes. They verify exact handled output, dependency absence, BOM/Unicode,
byte/line/table/title limits, no overwrite, paths and platform-specific I/O
behavior. Fictional DOCX packages are checked for ZIP integrity, XML content,
heading/list/table/layout conventions, neutral configured core fields, retained
template parts and absence of external relationships or newly embedded media.
Controlled child probes exercise no external actions, interruption, flushing,
Windows short writes and retained partial output.

Each lane selects 72 originals plus 30 copied-runtime methods: 102 methods,
816 across eight lanes. Required native fixtures cannot become capability
skips in hosted qualification. Exact OS-only cases remain skips on the other
OS; successfully queried absence of an alternate short spelling is separately
reported. Local Windows symlink privilege error 1314 is documented only for
local probes, and never substitutes for required hosted native execution.
Unexpected skips and failures stop qualification.

## Fresh dependency and archive gates

The source helper verifies a finite manifest of published text/source files.
The source ZIP is rebuilt with fixed entry ordering, timestamps, regular-file
attributes and compression settings. Every member must match the committed
allowlist. This determinism applies to the source ZIP, not generated DOCX ZIPs.

`packaging/dependencies.py --download NEW_EXTERNAL_WHEELHOUSE` selects the
host platform/CPython ABI, downloads exactly the three runtime wheels plus
the pinned installer, and verifies recorded bytes and SHA-256. Use
`--wheelhouse EXISTING_WHEELHOUSE` to verify an existing exact set. Downloads
are HTTPS requests made only by this explicitly requested helper.

`packaging/qualify.py` accepts `--packages`, `--wheelhouse`, `--workspace`,
`--report` and optional `--reference-build`. It uses an owned external
workspace, extracts the reviewed archive and creates a new no-pip application
venv. A separately hash-pinned installer installs only the matched runtime
closure from the wheelhouse using offline, binary-only, no-dependency and
require-hashes flags. Installed distribution versions and dependency consistency
are checked. Tests/imports must use the extracted runtime and that fresh
environment. Independent source builds must reproduce the ZIP and build
manifest. Optimization refusal and exact native skip contracts are also gates.

Dependency implementations, wheels and environments are not in the published
source ZIP. The full selected closure is pinned; installation is not a
vulnerability/advisory audit. Unsupported OS/architecture/ABI selections must
not fall back to another lane or bypass hashes.

## CLI and filesystem observations

Successful stdout uses the host's line ending. Windows script-entry handled
stderr uses LF; error categories can differ by backend. There is no version
flag. Static help remains available when document dependencies are absent.

All output is explicitly selected and newly created. There is no source-root
exclusion. Windows retains failed new output as unconfirmed. POSIX retains
its original same-identity cleanup attempt after a write failure. POSIX permits
regular hardlinked input; Windows requires single-link input. Canonical trusted
paths and stable local storage remain prerequisites. Do not infer atomicity,
hostile-filesystem isolation, exhaustive aliases, ACL privacy or durability.

## Publication acceptance

The public source inventory and five release assets undergo exact privacy
review. The release has a source ZIP, usage guide, build manifest, validation
record and checksums. The tag must resolve to the reviewed merged commit.
Anonymous downloads must match published digests and committed source, then
fresh downloaded-source acceptance verifies the package again. Raw diagnostics,
real Markdown/documents, environments and downloaded binaries remain private.

These checks qualify source packaging, dependency installation, fictional
runtime/CLI and OOXML package behavior. They do not accept Word/LibreOffice
visual rendering, real-document correctness, confidentiality or sharing rights.
