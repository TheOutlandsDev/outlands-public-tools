# Qualification contract — 0.1.0

This record defines release gates. Accepted `VALIDATION.json` attached to the
source release records actual outcomes for its reviewed commit; required
selections are not assumed passes. The unchanged [historical validation](VALIDATION.md)
and [manual export guidance](EXPORTING.md) remain distinct from fictional checks.

## Exact source and interpreter identity

The source ZIP contains 32 allowlisted source files plus `SOURCE-MANIFEST.json`,
33 members: original MIT runtime/Event-specific reader/helper, tests, authored
docs/generator and qualification/build helpers. It excludes interpreters, real
captures/event binaries, generated reports, raw logs and private methods.
Checksums/build manifest bind the exact ZIP; unsigned hashes show consistency,
not author authenticity, host identity or rights.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 with the
20261110 standalone archive recipe for Windows and Ubuntu. Preparation verifies
archive SHA-256, actual version and actual base executable SHA-256. Archive
lanes create new `venv --without-pip` environments with zero distributions.
No Python packages, native XML/Expat dependency, administrator permission,
global interpreter/PATH change or Windows event-log access is required.
CLI/generator uses `-E -s -B`; independent probes/helpers use `-I -B`.

## Preserved original and copied coverage

All 59 original methods remain: 27 timeline/CLI, fourteen restricted-XML and
eighteen support methods. Four runtime/generator files, three original test
files and five historical/example documents remain byte-identical to baseline,
including FORMAT, EXPORTING, PROVENANCE, VALIDATION and examples/README. The
native harness binds exact source/interpreter identity while selecting original
methods and assertions. The Event reader/helper are not replaced by VINTF's:
encoded CR is allowed in XML text but identifying metadata rejects controls;
JSON retains independent structure limits rather than XML physical-line limits.

Thirty copied-runtime methods supplement originals with external copies,
fictional owned fixtures and actual CLI execution. Each lane selects 89 methods;
four versions on Windows/Ubuntu select 712 total: 472 original and 240 copied
selections. Actual passes/skips/failures/errors remain separate. Finite named
platform-opposite FIFO/Windows-stream skips are allowed; local privilege skips
require the actual Windows symlink privilege error. Hosted strict mode permits
no such privilege skip; hardlink safeguards must execute. All skip-policy IDs
must be selected and unique.

Coverage includes saved JSON/XML equivalence, exact UTC offset/fraction/tick
arithmetic and wide decimal strings, stable ties, grouping/optional keys, strict
and disabled gaps, same-file computer/channel/record-ID duplicate/conflict scope,
cross-file identity isolation, missing identity and no silent deduplication.
Privacy checks cover defaults/details and always-omitted computers, raw payloads,
security/unknown values and local filenames. Parser checks cover strict JSON,
the custom XML subset, namespace/metadata coverage, one-pass references and
DTD/entity/CDATA/malformed refusal. Safe I/O and bounds cover aliases/links/
streams, immutable stable regular inputs, fixed errors, fresh reports, escaping,
input/report manifests and resource ceilings. No real export command is run.

## Exact executable guide

The [fictional guide](../USAGE.md) executes its exact published Python block in
a fresh no-pip 3.15.2 environment using copied actual runtime. Explicit whole
report expectations do not import/reuse the inspector/parser/timestamp logic.
Working evidence is preserved separately from one committed-head rerun, with
21 selected source hashes including EXPORTING and the actual qualifier.

Its 51 cases include fixture generation, 27 complete reports and twenty-three
controlled refusals. It checks 54 payload hashes, 28 input hash observations,
forty unchanged fixtures and 121 exact input/report files. Twenty default/seven
details reports include three observation-equivalent privacy pairs; saved
JSON/XML timelines/groups match in both modes. Computers/raw payload markers
remain omitted, including encoded CR payload text; details expose only accepted
fields. Identifying hashes/structure remain, so omission is not anonymization.

## Evidence limits and reproduction

All eight scope flags remain false: live event-log querying, native event-binary
decoding, native XML parsing, external resources, serialized computer names,
serialized raw payloads, real event logs and verified causal diagnosis. No
complete log capture, authenticity/clock accuracy, cross-file deduplication,
payload equivalence, runtime monitoring, successful deployment or failure cause
is verified. Gaps/group repetition are scoped observations, not causal findings.
Empty supported exports may exit 0 without establishing system completeness.

Use the [pinned Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
in a new owned external workspace. Review actual release workflow results;
public validation retains sanitized counts/versions/byte identities rather than
paths, machines, raw logs or real captures. Input/output checks are not an OS
sandbox, atomic hostile-writer snapshot, hard I/O deadline, transactional rollback
or durable-output guarantee. Failed writes may leave partial fresh directories;
only complete verified manifests establish report-byte consistency.
