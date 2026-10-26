# Python Helpers input hardening review

Only existing public MIT helper/native mechanisms and invented fixtures are
selected. No actual JSON, user record, credential, endpoint, configuration,
private helper, capture, model/corpus, asset, DLL or third-party implementation
is exported. TheOutlandsDev remains the MIT identity; required notices, held
original rights and existing release assets remain unchanged.

The loader preserves its signature, default/maximum byte limits, strict limit
validation, decoding/JSON rules, object requirement and displayed fixed errors.
The sensitive-key set and redactor function remain byte-identical. The original
combined 47-method regression file remains unchanged. Invalid path types now
map to the fixed load error; stricter path/ordinary-file rules are explicit
compatibility changes, not new JSON or redaction semantics.

Both platforms gain bounded ordinary-file reads with observed identity/size/
time/path checks. POSIX adds ancestor/link checks and available no-follow/
nonblocking flags. Windows adapts public native local-volume/path/reparse/name
checks with retained handles and CRT descriptor comparison. Source hard links
remain allowed; ADS arguments and named-stream scanning are excluded.
Interruption propagates as before and closes owned resources. No CLI, selected
input modification, generated report, install action or network operation is
added.

Local Windows/Python 3.12.7: all five original helper tests passed. New 40-method
suite: 30 passes/10 skips (six POSIX-only cases and four unavailable native
link/junction cases); short-name rejection ran. Windows/Ubuntu Python 3.12/3.13
CI requires native Windows link creation, with optional short-name/platform
availability explicit. Other versions are unverified. Exact-commit results are
recorded separately.

A separately copied two-file library passed 25 fresh processes: 22 direct API
consumers and three controlled read/EOF/interruption cases. Against a hash-
verified frozen public baseline, 100 fictional JSON cases and 100 redaction
cases matched complete API outcomes. Inputs/runtime stayed unchanged without
bytecode or generated files in selected trees. Local combined regression:
46 passes/one native-symlink skip; collection: 532 passes/27 skips;
documentation/JSON: 445 checks passed.

Publication uses exact selected-byte hashes, frozen/current public auditors,
private markers and manual dispositions. Real inputs, source mappings, output,
logs, reports, markers, captures and the audit ledger stay private. See the
[input contract](../tools/python-helpers/docs/INPUT-CONTRACT.md).

Redaction still retains unknown fields/free text and cannot establish anonymity,
confidentiality or rights. Sampled filesystem checks require stable trusted
local parents; hostile mutation, drive rebinding, live providers, blocking I/O,
power loss, total resource quotas and full metadata/stream backups remain
outside acceptance. No complete secret-detection or semantic IP claim is made.
