# OUTLANDS | Point-in-Time Observation Resolver

Resolve supplied pinned observation revisions at explicit availability cutoffs, with ambiguity visible. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional series; no private original implementation reused.

From this complete tool directory:

```text
python -B observations.py --input examples/input.json
python -B observations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` needs a trusted existing external parent and
a destination that does not exist. No original program, real dataset or model needed.

## Contract and interpretation

Library: `observations.resolve(raw_json_bytes)`. Exact fields:
format (`outlands-point-in-time-observations-v1`), observations, requests. Source
observations follow the shared revision/pin contract below. Requests are exactly
`{id, series, period, as_of}`, with period<=as_of. Request identity is id. At most
1,000 request rows; empty accepted requests requires review.

For each series/period request select the accepted revision with maximum declared
available_at <= as_of. Cutoffs are inclusive. Strict revision/availability order
is checked globally first: equal availability across consecutive revisions or
a later revision claiming earlier availability requires review, even for unused
or future rows. Input ordering never chooses a version. Missing/only-future
observations, source ID aliases, pin/revision conflicts and malformed requests
withhold every resolution. Exact identical source/request snapshots count once.
Unused valid observations are allowed. Do not pass an event log with conflicting
snapshots and expect an automatic latest-status overwrite.

Output contains request ID, as_of and a selected observation reference with ID,
series, period, revision, available_at and verified content pin; no value. The
example selects period-1 revision 1 at as_of 2, revision 2 at as_of 3. Revision
numbers need not be contiguous. The resolver does not establish a complete version
history, authenticated timestamps, actual publication timing or trustworthy source
content. It selects only among supplied claims and never updates source records.

## Shared data, identity and privacy boundaries

All periods, origins, targets, cutoffs and availability times are exact integer
ordinals 0..1,000,000,000. They have no implicit calendar, time zone, clock,
timestamp format or elapsed-time unit. Boolean/numeric coercion is refused.
IDs/series match `[a-z][a-z0-9_-]{0,47}`. Exact supplied cadence/cutoff semantics
remain the caller's responsibility; timing claims are not independently verified.

Resolver/lineage observations are exactly
`{id,series,period,revision,available_at,value,sha256}`. Revision is 1..1,000,000;
available_at>=period. This subset represents observations available at/after
their effective period, not known-future covariates. Value is a bounded decimal
string, absolute value <=10^12 with at most six fractional places. No exponent,
leading plus/whitespace/ambiguous zeros, nonfinite values or float coercion.
Trailing fractional zeros and negative zero normalize without caller decimal-
context rounding. SHA-256 must match canonical normalized payload without the
sha256 field: sorted-key compact ASCII JSON plus one LF (toolkit.encode).
Changing content, identity, timing or revision changes that pin. Input hashes
separately cover exact raw outer JSON. Hashes do not authenticate or anonymize.

Observation snapshot identity is (series,period,revision). ID must identify only
one accepted snapshot globally. Revisions for each series/period, sorted by
revision number, must have strictly increasing declared available_at. Ties or
reversals require review rather than guessed ordering. Future/unused invalid
snapshots also block resolver/lineage output. At most 1,000 observation rows.

For row lists, normalized identical identity snapshots become one accepted record
plus explicit duplicate_rows; conflicting identity groups withhold every member,
including identical repeats inside a conflicting group. Bad row shape/value/pin
is rejected with a fixed code and 1-based logical position. Every list satisfies
input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows.
Cross-reference/timing issues do not reclassify structurally accepted rows.
Row 0 denotes a cohort/policy issue. No silent truncation or latest conflict fix.

The grid checker intentionally retains coverage for valid quality findings, but
withholds it after malformed points. The other tools withhold their entire plan,
resolutions or lineage after any issue. Invalid outer contracts/policies/limits
refuse entirely. A PASS describes the supplied supported scope, never actual
availability, complete history, feature implementation, model quality or publication
approval. Real IDs, periods, gaps, references, counts and hashes can remain private.

## CLI and native file limits

Read one explicit JSON file <=4 MiB. Unknown fields, duplicate keys, JSON floats/
nonfinite values, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and
integers outside +/-10^18 are refused. Reports are escaped ASCII JSON <=8 MiB.
No source-system access, directory discovery, include/URI fetch, environment
expansion, clock, network, process/model launch, training, automatic forecast,
feature-value calculation or target action occurs in these tools.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted, quiescent parents. No hostile filesystem/process sandbox.
Default output is private stdout JSON. Optional --out exclusively creates a new
external report beneath an existing parent outside the source tree; no overwrite
or mkdir. Failed writes can retain partial/unconfirmed output; inspect privately
and select a fresh path. Windows inherits parent ACLs without a confidentiality
guarantee. Shell redirection lacks --out protections. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption; supplied paths/values are omitted from errors.

Reports omit observation values, but metadata is not anonymized. Keep real inputs
and reports private. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
