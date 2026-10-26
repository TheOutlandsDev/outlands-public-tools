# Batch 21: XML Recipe Inspector on Windows

This addition adapts only the existing public MIT inspector and native file
mechanisms. No original private recipe, image, derived record, identifier, path,
credential, configuration or vendor asset was selected/read/copied/run. No
third-party implementation, application, DLL or runtime is bundled.

## Behavior and preservation

Windows file I/O previously returned a platform rejection. Supported local-volume
XML now uses retained native ancestor handles, bounded regular single-link reads,
reparse/name/identity checks and raw-path refusal before normalization. Inputs,
output parents and destinations reject ambiguous/reserved/stream/alias spellings.

Inspection and complete bounded rendering precede new-directory creation. Native
directory creation refuses existing destinations; every fixed report uses
exclusive new-file creation with no sharing during writes. All report handles
remain until final identity/name/size checks, and output-directory/ancestor handles
stay held through file closure. Short/zero/failed writes and observed changes fail.
Missing parents are not created; Windows failure handlers never delete/roll back
pathnames or retry into an existing directory.

The original POSIX reader/writer bodies remain unchanged after their Windows
dispatch. All original pure XML parsing, calibration/geometry, numeric limits,
CSV escaping and JSON rendering definitions are byte-identical. The original
34-test file remains unchanged and runs on Ubuntu in CI. CLI arguments preserve
raw Windows spelling; static help/counts/errors remain, with a fixed interruption
category added.

## Fictional validation

The local Windows/Python 3.12.7 new suite discovered 50 methods: 46 passed and
four skipped, with no failures/errors. It comprises 38 native Windows and 12
portable methods. Skips were unavailable native hardlink/symlink/junction
creation and one POSIX-only API probe; skips are not passes. CI requires those
three Windows link fixtures and targets Windows/Ubuntu Python 3.12/3.13.
Unavailable alternate short-name spellings remain explicit skips. Ubuntu also
executes the unchanged original 34-method suite.

Portable fixtures cover retained geometry conventions, UTF-16/character
references, DTD/entity/external-entity/processing-instruction/namespace refusal,
numeric/depth/element/text/field limits and formula-like CSV text versus numeric
cells. Native fixtures cover redacted CLI findings, bounded inputs/output,
source/existing-file preservation, reparse/hardlink/alias refusal, retained handle
sharing and ownership/cleanup. Fault cases cover short/failed writes, flushing,
post-mkdir handle acquisition, unexpected children, file/directory identity
changes and close errors. Empty low-level byte payloads and the exact 4 MiB
combined output boundary are exercised. Failed exports retain their new empty,
partial or unconfirmed directory; no cleanup removes it. Repeated success/failure
runs showed no native handle-count growth in the fixture process.

A separate two-file runtime copy outside the checkout passed 37 fresh-process
Windows CLI scenarios using fictional XML only. It checked three/four-report
exports, geometry, CSV shielding/JSON retention, UTF-16, ordinary references,
declaration refusal, actual input/depth/element/field/output bounds, fixed errors,
path rejection and overwrite preservation. Source/runtime/input bytes remained
unchanged and no bytecode appeared. The text-character limit is separately
tested with a reduced bound; the CLI walkthrough does not claim independent
exhaustion of that limit under the existing raw-byte cap and entity prohibition.

The collection regression discovered 559 methods: 532 passed and 27 skipped.
Local documentation/JSON checks and Ruff checks/formatting of the new backend
and test file passed. These are separate observations from the new 50-method
suite. Independent static review found no material issues. Consult exact-commit
Actions logs for executed platform counts; none of these checks validates real
recipes, vendor behavior or measurement accuracy.

## Output/privacy and remaining limits

Directory creation and handle acquisition are separate operations. A hostile
ordinary-directory replacement in that gap can be indistinguishable; this is
not an atomic owned-directory transaction. Other processes can add child entries;
unlisted children are not enumerated. File handles close sequentially. Neither
backend provides an immutable report set, exact output-tree privacy guarantee,
hostile-filesystem sandbox or power-loss recovery.

Windows directory/report permissions inherit from the chosen parent's ACL, with
no POSIX 0700/0600 equivalent or confidentiality check. Use stable trusted local
paths and a private parent outside the checkout. File flushing does not prove
directory-entry/hardware durability. An error can leave a fully written but
unconfirmed set as well as partial output; inspect privately and retry with a
different new destination. Read the [Windows contract](../tools/xml-recipe-inspector/docs/WINDOWS.md).

Reports retain selected identifiers, locations, geometry and calibration-derived
values and are not anonymous. Library tracebacks can retain source locations
even though handled CLI errors suppress native/source values. Network/virtual
storage, mount/drive rebinding, hostile concurrent mutation, mapped views, ACL
privacy and exhaustive filesystem behavior are not certified. Parsing does not
establish authorization, ownership, vendor accuracy or release readiness.

The exact changed publication bytes receive an unchanged-detector/private-marker
review and hash inventory. Private markers, scanner outputs, mappings, receipts
and ledgers stay outside the repository. This addition does not clear unrelated
imports, Git history, held source/rights families or existing v0.1.0 assets.
Selected original work remains MIT under TheOutlandsDev.
