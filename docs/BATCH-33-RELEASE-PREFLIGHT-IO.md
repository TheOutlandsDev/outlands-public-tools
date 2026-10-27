# Batch 33: Release Preflight file handling

This update uses only existing public MIT code and newly invented packages.
The [preflight tool](../tools/release-preflight/README.md) retains external
hash pins, manifest/launcher rules, update-plan decisions and plan-only behavior.
No original operational script, real manifest, server configuration, credential,
launcher argument, deployment path, game/plugin asset or record is selected.

Windows gains native-handle file/directory checks, stricter path spellings,
observed alias/root separation, checked streamed reads and guarded new reports.
The backend preserves existing public release-auditor functions and adds only
selection, protected-report and root-separation adapters. POSIX retains its
protections and adds retained descriptors, ancestor rechecks, bounded read
loops and verified exclusive report writes. Report bytes remain compatible.

See [I/O checks and limits](../tools/release-preflight/IO-SAFETY.md) for exact
path restrictions and unconfirmed-output behavior. Only explicitly requested
private reports are written. Nothing is downloaded, executed, installed,
scheduled, replaced or deleted by the tool.

Validation uses the unchanged original 28 methods, 47 new fictional methods,
and a Windows/Ubuntu Python 3.12/3.13 matrix requiring native links/junctions.
Local original suite: 26 passes/two native skips. New suite: 31 passes/16
platform or native-feature skips. A copied two-file runtime passed 24 fresh
processes. Across 100 fictional package trees, verify/plan/launcher results and
report bytes matched frozen public source. Runtime/input bytes stayed unchanged
without bytecode. Comparisons are retained privately with runtime hashes; CI
evidence must be reviewed before merge. No live game/server or deployment
acceptance is claimed.

Publication is limited to the exact source/documentation/test diff. Frozen and
current auditors are compared using private markers. Invented negative-path
flags must be reviewed against exact file hashes; no rule is disabled to hide
them. Generated packages, reports, markers, logs, comparisons and captures stay
outside publication. This does not clear held original source families or inputs.
