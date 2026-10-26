# Batch 32: Server Maintenance Planner input hardening

This update uses only the existing public MIT planner and public native input
guards with freshly invented requests. Original server/game scripts, service
configuration, player records, credentials, endpoints, schedules, backups,
assets and operational plans are not selected, copied or executed.

The [planner](../tools/server-maintenance/README.md) retains its lifecycle,
readiness and calendar rules and plan-only results. Native Windows reads now
retain checked file/ancestor handles and match a binary CRT descriptor, with
strict path/alias/reparse checks. POSIX retains its protections and adds final
ancestor checks. JSON parsing rules and the 64 KiB input cap are preserved.
Windows interruption/help behavior is fixed and documented. There are no
network, process, service, scheduling or output-file features.

See [input checks and limits](../tools/server-maintenance/INPUT-SAFETY.md) for
the stricter Windows path boundary, library error boundary and supported
stable hard links. These are sampled read guards, not a filesystem sandbox,
operational verification or a confidentiality audit.

Validation uses the original 15 maintenance methods plus 46 new fictional
methods and a Windows/Ubuntu Python 3.12/3.13 CI matrix. A copied two-file runtime
passed 30 fresh processes. Against frozen public source, 7,680 lifecycle plans,
1,344 calendar cases, 16 readiness combinations and 100 decoded JSON cases
matched; runtime/input bytes remained unchanged without bytecode. Local new
suite: 35 passes/11 platform or native-feature skips. CI must run the required
native link/junction cases and record optional short-name availability.

Only an exact reviewed source diff is eligible for publication. Frozen and
current release auditors are compared with private markers; harmless fictional
negative-path flags must be dispositioned against exact file hashes. Generated
inputs, comparison reports, markers, logs and captures stay outside publication.
This update does not clear any held original source family or private input.
