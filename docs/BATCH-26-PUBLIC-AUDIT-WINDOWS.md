# Public Release Audit Windows hardening review

Only existing public MIT auditor/native mechanisms and invented disposable
fixtures are selected. No real export/marker list, private path, credential,
user record, configuration, capture, original helper, game asset or third-party
implementation is exported. TheOutlandsDev remains the selected MIT identity;
required notices remain. Held originals/rights and release assets are unchanged.

The detector function, patterns, filename policies, example-address exceptions
and manifest validator remain byte-identical. POSIX export scanning/report
writing retain their bodies. JSON controls gain bounded ordinary-file reads
and identity checks on both platforms; Windows refuses multiply linked controls.
JSON schemas/parsing semantics remain otherwise unchanged.

Windows adds local-volume/path/reparse/name checks, scoped native handles,
bounded directory enumeration, native/CRT identity around text reads and a
total budget charged even for failed reads. Selected export hard links remain
separate names; only unnamed data is hashed. The pattern engine is unchanged.
Reports gain native overlap checks, a 64 MiB encoding ceiling, exclusive new-file
creation, short-write handling, flush requests and observed identity/name/size/
link-count checks. Errors retain partial or complete-looking unconfirmed output.
Windows interruption returns a fixed status 130 result and closes resources.

Before editing, the public auditor was frozen and hash-verified. Full results
match on 100 generated stable trees. A separate two-file copy passed 25 fresh
processes: 22 direct CLI and three partial-write/late-flush/interruption cases.
Input/runtime bytes stayed unchanged and no bytecode appeared. The original
combined 47-method suite remains byte-identical: 46 passed/one native-symlink
skip locally. New 40 methods: 29 passed/11 skips locally, including eight
unavailable native link cases and three POSIX-only cases; short-name rejection
ran. These are Windows/Python 3.12.7 results, not native-link acceptance.
Windows/Ubuntu Python 3.12/3.13 CI requires native Windows link/junction cases;
optional short-name and platform availability are reported separately.

Publication review uses the frozen scanner, revised scanner, unchanged private
markers and exact selected-byte hashes. The changed scanner is not its own
sole release authority. Reports, markers, generated fixtures, captures, review
dispositions and the ledger stay private. CI/merged bytes are checked separately.

Read the [filesystem contract](../tools/public-release-audit/docs/WINDOWS.md).
Sampled checks, ACL/version-dependent permissions, nontransactional output,
native blocking, hostile mutation, live providers and power loss remain limits.
Finding snippets are omitted, but filenames can contain private identifiers
and hashes can identify content. Reports need their own sharing review; no
semantic-IP, anonymity, ownership or complete secret-detection claim is made.
