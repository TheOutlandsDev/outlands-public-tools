# OUTLANDS | Recommendation Feedback Reconciler

Reconcile exact recommendation revisions, decisions and outcomes without actions or training. Independent CLI/library; Python 3.12/3.13 standard library only,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional examples

From this tool directory:

```text
python -B feedback.py --input examples/input.json
python -B feedback.py --input examples/needs-review.json
```

The first returns PASS/exit 0; the second REVIEW_REQUIRED/exit 1. Only invented
records/contracts are supplied. No private original implementation, model,
history, business rule, mapping, source path, user/customer record, credential,
operational configuration or third-party asset is included. Private originals
are not opened, imported, modified or executed. Combined packaging is deferred.


## Revision-bound feedback

Library: `feedback.reconcile(raw_json_bytes)`. Exact fields:
`format: outlands-recommendation-feedback-v1`, `recommendations`, `decisions`,
`outcomes`. All identities are the exact pair recommendation_id/revision.
Different revisions may coexist and are never matched by a latest-version rule.
Recommendations contain symbolic `action`; it is opaque data, never executed.
Decisions contain accept/reject/defer. Outcomes contain status pending/observed
and `observed`: null for pending, a decimal string for observed.

Every row also contains recommendation_id and an exact positive revision <=
1,000,000. Each recommendation revision has one selected action, decision and
outcome snapshot. Normalized identical repeats count as duplicates. Different
actions/decisions/outcomes under one identity conflict and all members are
withheld. A pending and observed row for one identity is a conflict, not an
automatic overwrite; select a reviewed snapshot explicitly. This is not an
append-only event log or persistence service.

Decisions/outcomes must refer to an existing exact recommendation revision.
Every supplied outcome, including pending, requires an accept decision.
Orphans, wrong revisions, conflicts and rejected rows require review and withhold
**all** derived states. Raw row accounting and fixed issue positions remain.
Valid pending work can return PASS for structural reconciliation without claiming
completion. At least one recommendation is required; decisions/outcomes may be empty.

| Evidence | Derived state |
| --- | --- |
| No decision | AWAITING_REVIEW |
| Defer / reject | DEFERRED / REJECTED |
| Accept, no observed outcome | ACCEPTED_PENDING_OUTCOME |
| Accept, matching observed outcome | OUTCOME_RECORDED |

`all_acceptances_have_observed_outcomes` requires at least one accepted revision,
all accepted revisions observed, and no issues. It says nothing about deferred or
unreviewed recommendations. Output omits action and outcome body values; IDs,
revisions, state counts and fingerprints still need private handling.
No outcome truth, causal effect, action execution, model training, policy update
or real improvement is established. Review decisions are caller assertions, not
authenticated identities. No database, live feedback stream or recovery replay.


## Shared parsing and file limits

At most 1,000 rows per supplied list. Each list's input rows equal accepted unique
records + duplicate rows + conflicting rows + rejected rows. Conflicting groups
include all members, including repeated variants. Row positions are one-based
logical list positions. Malformed row structures/values produce fixed rejection
codes without echoing supplied values; malformed/ambiguous top-level JSON fails
entirely. No silent truncation or partial derived summaries after an issue.

Identifiers match `[a-z][a-z0-9_-]{0,47}`. Decimal values are strings, absolute
value <= 1,000,000,000,000, at most six fractional places; no exponent, whitespace,
leading plus, leading zero ambiguity, nonfinite value or numeric/boolean coercion.
Negative zero and trailing decimal zeros normalize for duplicate comparisons.
JSON refuses duplicate keys, floats/nonfinite numbers, invalid Unicode, excess
depth (32)/nodes (100,000), strings over 4,096 characters and unknown fields.
The selected file is at most 4 MiB. Reports serialize as ASCII JSON, at most 8 MiB.
Counts remain JSON integers; exact fractions use decimal-integer strings.

See [checked Windows/POSIX I/O](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). The CLI reads only the explicit ordinary single-link
input. No tree discovery, environment expansion, service, network, clock,
process execution or source-system query. Inputs/parents must be trusted and
quiescent; guards do not promise hostile-filesystem containment.

Default output is private stdout JSON. `--out` exclusively creates a new external
private report under an existing parent, outside the source tree. No directory
creation or overwrite. Failed writes can retain partial/unconfirmed output;
inspect privately and select a new path. Windows ACLs inherit from the parent;
no confidentiality guarantee. Shell redirection does not inherit --out guards.
Source pins, body-value omission and JSON escaping do not anonymize data, verify
rights or authorize publication. Aggregates, policy labels, IDs and hashes can
still disclose private information. No real-world effectiveness is qualified.

Exit 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Argument errors
omit supplied paths/values. These are offline descriptive tools, not deployment,
production acceptance, automatic remediation or statistical reliability proof.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
