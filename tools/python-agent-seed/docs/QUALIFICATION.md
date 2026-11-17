# Qualification populations and limits

Four native profiles use pinned complete CPython 3.12.16 and 3.15.2 on Windows x64
and Ubuntu x86-64. Every job requires matching independent ZIP/build-manifest
rebuilds, a fresh extraction, a new venv without pip and zero installed third-party
distributions. Each confirms original/raw source pins and immutable source after
checks. Release VALIDATION.json records actual commits, jobs, interpreter pins,
population outcomes and executed IDs; this document alone is not a passing record.

Positive population per profile: eight original example methods, 18 original
evaluation methods against separate reference repairs, and ten release/CLI methods:
36 passes, zero positive failures/errors, zero skips and zero unexpected warnings.
Reference IDs and source tests remain unchanged. The new release tests cover source
pins/counts, independent exercise copies, existing/package-internal/unknown/linked
destinations, copied CLI/error privacy, altered starter-baseline refusal, repaired
copy workflow, JSON/CSV link metadata agreement and modified-source refusal.

The unchanged starter population is not included in those positive totals. Eighteen
declared methods produce eight actual method starts and two failed-import entries,
ten framework entries total. The fixed expected baseline is one pass, three
assertion failures and six errors, including two import failures for missing result
classes. Ten declared methods cannot run in the untouched starters. Every observed
ID/type/count must match STARTER-CONTRACT.json; an unexpected outcome fails package
qualification. The expected errors stay visible and are never counted as passes.

Each fixed fixture probe verifies three refused audit canaries (unreviewed child
process, synthetic socket event and excluded bad-example filename) before running
tests. Only the exact good-example Python print child is permitted. Windows and
POSIX audit payloads differ; the first Windows guard version refused that harmless
command. Its seven-pass/one-error observation remains private. The guard now compares
the exact Windows command line or POSIX argv; original examples were not changed.
There must be zero unreviewed runtime attempts and warnings in every probe. Audit
hooks/private working directories are not OS containment or a general untrusted-code
runner. The synthetic socket event makes no real connection. Excluded bad examples
are not imported/executed. Native link creation is additionally tested when the
host permits it; the reparse refusal branch always runs without skipping a method.

The unchanged integrity/example scripts, catalog regeneration in a disposable copy
and original evaluation template with a separate reference copy also run. Real
models, training, retrieval, external-source contents, toolchain lint/type-check
quality, hostile-file containment and production readiness are not qualified.
Reference answers are shipped visibly, so these small exercises are practice and
regression fixtures, not evidence of unseen-agent performance or a held-out benchmark.
