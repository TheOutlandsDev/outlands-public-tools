# Documentation Check filesystem hardening review

Only existing public MIT checker/native mechanisms and invented documentation
fixtures are selected. No real documents, directory mappings, operational
templates, records, credentials, captures, original private helpers, assets,
DLLs or third-party implementations are exported. TheOutlandsDev remains the
MIT identity; required notices and held original rights remain unchanged.
Existing release assets are unchanged.

The limited Markdown/JSON grammar, exclusions, file/entry limits, sorting,
finding/report fields and original combined 47-method test file remain
preserved. The POSIX path-check body remains; both platforms gain actual bounded
reads and collection-before-sort limits. POSIX adds available no-follow/
nonblocking flags and identity/directory checks. UTF-8 BOM/newline conversion,
JSON duplicate-key handling and nonstandard-constant rejection remain.

Windows adds scoped native metadata/name/identity guards. Local targets use
attributes without data reads and must remain ordinary files/directories under
the observed native root. Unsafe Windows target spellings and observed reparse/
alias/overlap failures map to the existing target finding. Hardlinked sources
and targets remain supported; named streams are outside scan scope. The checker
never writes a selected tree/report. Handled Windows interruption returns a
fixed error/130; POSIX interruption behavior is preserved.

Local Windows/Python 3.12.7: all five original documentation methods passed; new
40 methods had 27 passes/13 skips, comprising eight unavailable native link/
junction cases and five POSIX-only methods. Local short-name rejection ran.
Windows/Ubuntu Python 3.12/3.13 CI requires native Windows link/junction creation,
with optional short-name/platform availability explicit. Other versions remain
unverified. Standalone/exact-commit CI evidence is recorded separately.

A separately copied two-file runtime passed 22 fresh processes: 19 direct CLI
invocations and three controlled read/entry-limit/interruption cases. A
hash-verified frozen prior checker matched complete results on 100 fictional
stable trees. Input/runtime bytes stayed unchanged without bytecode or generated
files in selected trees. Local combined regression: 46 passes/one native-symlink
skip; collection: 532 passes/27 skips; documentation/JSON: 443 checks passed.

Publication uses exact selected-byte hashes, independently frozen/current public
auditors, private markers and manual dispositions. Actual documents, outputs,
captures, marker lists and the audit ledger stay private. Pattern silence and
PASS do not clear confidentiality or source rights.

Read the [filesystem contract](../tools/documentation-check/docs/FILESYSTEM.md).
Trusted stable local parents remain required. Sampled checks are not atomic
tree snapshots, hostile-filesystem protection, total resource quotas or
live-provider/power-loss acceptance. Findings retain private filename metadata;
no anonymity, complete secret detection or semantic IP guarantee is made.
