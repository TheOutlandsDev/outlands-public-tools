# Manufacturing Review Demo 0.1.0 for Windows x64

Extract one ZIP and open **Manufacturing Review Demo.cmd**. Bundled Python runs
both existing fictional exercises, then opens an offline page of the actual
results. No Python installation, pip, account, PATH change or network is needed
for application use. This is an unsigned portable application, not an installer.

The bundle contains exact public source for twelve independent tools and both
unchanged exercise runners from Toolkit 0.9.0. CPython 3.14.10 binaries/notices
remain exact. A local module-path adapter supports the original tool entrypoints
inside the isolated embedded runtime; no system/user Python is selected.

Expect 36 CLI calls with 17 retained REVIEW_REQUIRED outcomes. A successful
exercise reproduces the expected failures. Capacity conflicts, canonical-lot
overreservation, incomplete inspection coverage, selected failed readings and
rework/scrap reconciliation remain inspectable. Operator review stays REQUIRED.

Every launch creates a fresh private run folder. Original inputs, CLI reports,
receipts and hashes stay together; saved runs can be verified and reopened
without replay. Existing folders are refused unchanged. A run manifest proves
byte consistency only; actual inputs and reports still need a separate sharing
review. No actual production, stock, delivery, inspection, repair, physical
genealogy, acceptance or publication authority is established.

CI checks matching Windows and Linux ZIP builds, the actual bundled-runtime
Windows launcher, and Chromium rendering of the saved report. The native checks
cover refusal of existing workspaces and changed saved runs. The browser checks
verify that the local page makes no remote requests. Publication is on hold.

Windows containers retain an unsupported virtual NT volume namespace, including
when supplied a new NTFS scratch disk. The unchanged guards refuse that storage;
the failed observations remain linked in CONTAINER-VALIDATION.md. Read the
acceptance records for the checks and their results.

Earlier Toolkit and Windows releases stay unchanged. This focused bundle does
not package the newer service tools marked pending in the live catalog.
