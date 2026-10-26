# Documentation Check filesystem contract

Python 3.12+, standard library only. Keep `docs_windows.py` beside
`docs_check.py`. Only existing public MIT mechanisms and fictional fixtures are
selected. No actual document tree, mapping, report, configuration, credential,
record, original helper, capture or third-party implementation is bundled.

## Preserved rules

Markdown/JSON parsing, exclusions, selected suffixes, case-sensitive name sorting,
finding order, relative filenames/line numbers, report fields and original five
documentation tests are preserved. The original combined 47-method regression
file stays unchanged. The POSIX path/link check body remains preserved; selected
file reads and directory enumeration gain checks on both platforms.

UTF-8 BOM handling and universal newline conversion remain. JSON retains default
duplicate-key behavior and rejects the same nonstandard NaN/infinity values.
Markdown retains its limited inline/image/reference-definition grammar and
fence/inline-code handling. HTTP/HTTPS/mail links are skipped without fetching.
Local links retain lexical root containment. This is not a full CommonMark,
reference-use, anchor, external-site or JSON-schema validator.

## Bounded read-only operation

The 10,000-entry and 2 MiB per-selected-file constants remain. Directory
enumeration collects no more than the remaining budget plus one rejection
probe before sorting. Excluded entries still consume the encountered-entry
budget. Overflow returns the existing fixed input/output error, not a truncated
PASS result.

Reads check ordinary-file identity/size before and after actual bounded I/O.
One excess rejection byte can be consumed; excess is never decoded. Files
initially too large/nonregular retain `SIZE_OR_TYPE`. Growth, observed file
mutation, decoding and read failures produce `READ_ERROR` without incrementing
the checked-document count. Directory/root failures can instead produce the
fixed command error. No selected tree, report or manifest is written. Reads can
affect OS access metadata. These per-file/entry bounds are not total byte, CPU,
result-size, elapsed-time or process-memory quotas.

POSIX retains link checks and adds available no-follow/nonblocking open flags,
noninheritable descriptors, file/path identity checks and directory rechecks.
POSIX local targets retain existence checks, including nonregular targets that
are not opened for data. POSIX interruption behavior remains unchanged.

## Windows paths and local targets

Supported local fixed/removable drives require fully spelled paths. UNC/device
spellings, drive/root-relative forms, traversal in root arguments, ADS syntax,
reserved names, trailing dots/spaces, invalid controls, surrogate text and
observed reparse/short-name aliases are refused. Bounds are 4,096 characters,
64 components and 255/component. Relative child paths remain supported against
the working directory; Windows filesystem-root scans are refused.

Public native mechanisms retain checked ancestors/root/directory/file handles,
compare normalized volume names and binary noninheritable descriptors, and
reject observed identity/name changes. Data reads allow source hard links and
cover unnamed data only. Named streams, ACLs, ownership and full metadata are
outside scan scope.

Local link targets use native metadata access without reading target data.
They must be ordinary files/directories under the observed selected native
root. Encoded path normalization and lexical containment rules remain; unsafe
Windows target spellings, reparse ancestors/leaves, observed aliases and native
overlap failures map to `MISSING_OR_LINKED_TARGET`. Target contents, formats,
schemas and referenced application behavior are not validated. A linked or
reparse entry is still flagged before directory exclusion, including root Git
metadata. Windows native errors omit exception values and paths; handled
interruption returns exit 130 with `ERROR` / `DOCUMENTATION_CHECK_INTERRUPTED`.
Other exit codes remain 0/PASS, 1/findings and 2/fixed input/output error.

## Privacy, evidence and limits

Reports retain relative filenames and line numbers, which can themselves contain
private identifiers. Output is not redacted or anonymous. Keep actual reports,
documents, mappings, marker lists and captures private; a public export needs
its own content/rights review. PASS is documentation hygiene, not security,
secrecy, semantic IP or application acceptance.

Tests use invented documents and disposable trees. Local Windows/Python 3.12.7:
the five original methods passed; new 40 methods had 27 passes/13 skips. Eight
native link/junction cases were unavailable, plus five POSIX-only methods;
local short-name rejection ran. Windows/Ubuntu Python 3.12/3.13 CI requires
native Windows link/junction cases and reports optional short-name/platform
availability separately. Other versions remain unverified. Windows temp paths
can use 8.3 names: select a fully spelled private parent; CI uses canonical
temporary paths without relaxing alias checks. Exact-commit evidence is
reviewed separately.

A separate two-file runtime copy passed 22 fresh processes (19 direct CLI,
three controlled failures). A hash-verified frozen public checker matched full
results on 100 fictional stable trees. Input/runtime bytes stayed unchanged,
without bytecode or generated files in selected trees. Local combined regression
had 46 passes/one native-symlink skip; collection had 532 passes/27 skips;
documentation/JSON checks: 443 passed.

Stable trusted local parents remain required. Checks are sampled, with
pathname/open windows, not an atomic tree snapshot or hostile-filesystem
sandbox. Directory membership/content can change between observations; excluded
material is not validated. Drive-map rebinding, live/remote/cloud providers,
blocking filesystem calls, hardware/power loss, Git history/assets and complete
secret/IP clearance remain outside acceptance. No deadline covers every I/O.
