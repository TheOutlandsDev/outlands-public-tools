# Batch 22: Windows hardening and native Document Builder validation

This addition adapts only the existing public MIT builder and native file
mechanisms. No original document, logo, personal profile, private path,
credential, operational data or unselected template was read/copied/run or
included. Generated fictional DOCX files and private review evidence remain
outside the public checkout. No dependency implementation/runtime is bundled.

## Behavior and preservation

Windows no longer relies on generic symlink-only path checks. Raw paths receive
lexical validation, followed by retained native ancestor/file handles, regular
single-link input checks, reparse/alias refusal and normalized name/identity
observations. Input reads retain the existing 256 KiB bound, and empty Markdown
remains supported. Windows decoding mirrors the unchanged original read tail's
UTF-8/BOM, line/character and control-character checks.

The complete DOCX is rendered before native exclusive `.docx` creation. The
writer handles short writes, rejects failed/zero writes, flushes and verifies
stable identity/name and exact size before closing with ancestors retained.
There is no overwrite fallback, parent creation or Windows pathname cleanup.
Post-creation errors retain partial or fully written but unconfirmed new files.
Low-level empty bytes remain supported and no new DOCX output cap is introduced.

The original Linux path/read/write bodies remain unchanged after Windows-only
dispatch. Pure Markdown parsing, table validation, layout/style helpers,
document creation and neutral core properties are byte-identical. The original
27-test file, declared requirement and fictional example are unchanged. CLI
interruption has a fixed category, and the Windows script entry point emits
fixed errors with LF endings, preserving the original fresh-process test's
cross-platform bytes. The Linux entry point does not change that stream setting.

## Fictional execution and package inspection

Local Windows/Python 3.12.7 executed the unchanged original suite: 27 discovered,
23 passed and four skipped (three unavailable symlink cases and unavailable
FIFO creation). The new suite discovered 45: 41 passed and four skipped (three
unavailable native hardlink/symlink/junction operations and a POSIX-only API
probe). Skips are not passes. New cases comprise 35 native Windows and ten
portable methods.

Fixtures cover parser/layout/core-property/relationship behavior, empty Markdown,
input/line/table limits, raw-path and reparse/alias/hardlink refusal, conflicting
writers, no-overwrite/source preservation and missing parents. Fault cases
exercise short/zero/failed writes, flushing, CRT transfer, identity/name and
close failures, with new unconfirmed output retained. Repeated success/refusal
cases showed no native handle-count growth in the fixture process. This is
sampled execution evidence, not exhaustive filesystem or leak proof.

A separate copied runtime pair passed 40 fresh-process fictional scenarios:
37 direct CLI cases, two missing-dependency cases and one controlled interruption.
Nine generated DOCX packages passed ZIP/XML inspection for text, heading styles,
tables, core fields, relationships and absence of observed source/output/runtime
paths. No supplied remote media, macro, embedded object or external relationship
was introduced. Repeated exports had equal uncompressed part hashes; whole ZIP
bytes are not claimed reproducible. Runtime/source/input bytes remained
unchanged and no bytecode appeared.

The observed local runtime supplied python-docx 1.2.0, lxml 6.0.2 and
typing_extensions 4.15.0; no package was installed locally. CI targets
Windows/Ubuntu Python 3.12/3.13, installs only the declared direct requirement
and records executed transitive versions. Original and new suites run separately
on all four jobs. Windows requires native hardlink/symlink/junction fixtures;
unavailable alternate short-name spellings remain explicit skips. Consult
exact-commit Actions logs for actual counts and dependency observations.

The collection regression and documentation/JSON checks are recorded separately
in the private review. Ruff checks/formatting of the new backend/test file passed.
Independent static review found no material issues. No Word/LibreOffice visual
rendering, real document acceptance or dependency vulnerability clearance is
established by package inspection or these observed versions.

## Privacy and remaining limits

Core properties remain neutral OUTLANDS values with fixed dates and configured
empty fields, but Markdown/title text is copied and not anonymized. Default
template application fields, thumbnail/custom XML, styles and package parts
remain; ZIP member timestamps also remain. Fictional package checks record
those limits and do not scrub OOXML or certify every future document/dependency.
Real content, identifying metadata and sharing rights need separate review.

Windows output permissions inherit from the chosen parent's ACL; there is no
POSIX 0600 equivalent, ACL confidentiality check or encryption. Select stable
trusted local input/output parents and keep generated files outside GitHub.
Errors leave a new empty/partial/fully written but unconfirmed file for private
inspection; use a different new filename on retry. File flushing does not prove
directory-entry/hardware durability or power-loss recovery. See the
[Windows contract](../tools/document-builders/docs/WINDOWS.md).

Network/virtual storage, drive/mount rebinding, hostile concurrent mutation,
mapped views, ACL privacy and exhaustive filesystem behavior remain outside
the guarantee. Library tracebacks/unexpected runtime failures can retain source
locations. This is not an atomic snapshot, hostile-filesystem sandbox,
document-authenticity or public-release gate. Office visual layout remains
unverified even though original layout code and XML fixtures are preserved.

The stale historical licensing line now reflects selected original MIT material
under TheOutlandsDev; required upstream notices remain. The exact publication
bytes receive an unchanged-detector/private-marker review and hash inventory.
Private markers, scanner outputs, mappings, receipts and ledgers remain outside
the repository. This addition does not clear unrelated imports, Git history,
held source/rights families or existing v0.1.0 assets.
