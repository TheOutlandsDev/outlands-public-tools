# Provenance and license scope

Release Preflight is a fresh neutral implementation of local release and
launcher-review methods. Read-only historical review informed its specification;
original vendor downloaders, deployment configuration, installation/process
controls, monitoring, telemetry, credentials, schedules, game/plugin code and
vendor assets were excluded. Original operational scripts were not executed.

Standalone preparation starts from public baseline
`42d78431e2a9a3383d2b61b334e85b95b754cd8f`. It narrowly changes the top-level
source-boundary constant block, adding `_SOURCE_DIRECTORY` and revising
`REPOSITORY` to recognize literal structural `tools/release-preflight`
collection placement and otherwise protect the enclosing standalone runtime
directory. All `preflight.py` function bodies, `preflight_windows.py` bytes and
three original example files retain their reviewed baseline contracts/bytes.
Whole-core byte identity is not claimed across this scope fix. No manifest,
launcher, pin, payload-decision, report-encoding or native-backend repair is
introduced. Historical [IO-SAFETY.md](../IO-SAFETY.md) retains its wording/evidence,
including the earlier collection-layout statement.

The original 28 shared regression methods and 47 local I/O methods are retained
for standalone execution, with only required test scaffolding adapted. Original
75 method ASTs and 103 assertion calls are preserved: 97 in test methods and six
in helpers. Sixteen helper keys retain explicit provenance: five `regression:`,
eight `io:` and three `shared:` helpers. Exact maps/counts are bound by
source/native receipts; copied consumers independently exercise the two-file
runtime. The versioned `python-ast-fields-json-v2` encoding retains all actual AST
fields and adds `is_lazy: 0` only to legacy `Import`/`ImportFrom` nodes lacking
that field, representing their eager-import default. Python 3.15's explicit zero
then agrees with earlier imports; actual nonzero values remain distinct. No
field is dropped or hash waived, and within-version body equality remains
required. Cross-version full preservation objects/maps must also agree.
Applicable native
capability must execute under hosted strict skip contracts without changing
device policy. Actual results are in release `VALIDATION.json`, separate from
historical collection/I/O evidence.

Selected first-party source, tests, docs and fictional examples retain full
[MIT terms](../LICENSE), copyright TheOutlandsDev. The owner reports personal
work created with AI assistance; preparation/qualification also used AI
assistance without exclusive-authorship claims. Existing public MIT patterns
retain their notices. Python/stdlib/native OS APIs keep their own terms and are
not bundled as binaries. Operator inputs/third-party material are not relicensed
or cleared by this grant.

Pins prove agreement with supplied bytes, not authenticity, licensing,
authorization, malware absence or executable behavior. The utility does not run
candidate code or apply/reverse a release. Actual package trees, launcher values,
deployment topology, reports, credentials, logs and held source remain private
and outside the selected public scope. Fresh source-only qualification does not
establish application consistency, trusted suppliers, live integration or safe
deployment.

See the historical
[original review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-8-REVIEW.md),
[I/O review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-33-RELEASE-PREFLIGHT-IO.md)
and [collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md).
See [PRIVATE-WORKSPACE.md](PRIVATE-WORKSPACE.md) for input/output privacy and
[QUALIFICATION.md](QUALIFICATION.md) for the fresh release evidence boundary.
