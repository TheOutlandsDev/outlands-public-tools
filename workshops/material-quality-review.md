# Five-minute fictional material-to-quality review

Who this is for: a reviewer who wants to inspect material accounting and quality
reporting decisions using invented declarations. This is an original public
demonstration, with no workplace code, schema, records or equipment specifications.
It does not create a manufacturing execution system or operate equipment.

## Requirements and quick start

Download the complete Toolkit 0.9.0 **source ZIP** and SHA256SUMS.txt from its
release. Verify the checksum before extracting into a new folder. Supply Python
3.12/3.13 separately; this exercise uses the standard library and needs no pip,
account, network or service. Windows runtime bundles are separate applications.
From the complete package root:

```text
python -B workshops/material_quality_review.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

Replace the last argument with a new absolute path under an existing trusted,
ordinary parent outside the package. Existing destinations are refused without
changing their bytes. Use quiescent local storage; the runner is not a hostile
filesystem sandbox. Windows inherits parent ACLs without a confidentiality claim.
On failure retain the private directory, inspect the fixed error and use a fresh
destination. No cleanup or automatic retry overwrites earlier evidence.

## One authored workflow, eight distinct questions

1. **Requirements:** four invented kits require four motors and eight filters.
   A deliberately cyclic BOM withholds all requirements. Only explicitly selected
   leaves become material demand; intermediate modules are not counted again.
2. **Identities:** two motor aliases resolve to one four-piece canonical lot.
   Conflicting quantities under the same lot ID withhold the entire identity map.
   Identical replay counts once. Distinct canonical IDs cannot establish whether
   physical stock was duplicated; no tool can inspect those physical identities.
3. **Allocation:** two alias-based claims reserve five motors against four while
   the filter claim is one short. A separate corrected proposal reserves four and
   eight. Identity and allocation reports use the same lot-contract hash. The
   application does not allocate stock or apply these declarations.
4. **Handoff:** explicitly select that canonical motor ID and reserved quantity.
   A three-piece receipt against four declared pieces withholds totals. The
   corrected receipt accounts for four; identical event replay does not add four
   more. A structurally consistent receipt is not independent delivery evidence.
5. **Measurements:** four invented specimens use a teaching rule `[1,3)` in
   `demo-units`. Values 2 and 1 pass; 3 and 0 are outside. A separate selected
   later reading changes the third value to 2; the fourth remains outside. These
   are arbitrary teaching values, not engineering limits or verified readings.
6. **Coverage:** retain the missing fourth record, then all four initial records.
   Complete records still contain two outside outcomes; the later selection
   contains three within and one outside. Each record pins the exact retained
   measurement report. The runner recomputes those bytes; the coverage tool itself
   does not read them or verify their truth. Completeness is not acceptance.
7. **History:** two first-pass results, one failed/reworked/reinspected result,
   and one failed/scrapped result form an explicitly authored teaching protocol.
   An incorrect reinspection attempt withholds the whole cohort. The corrected
   history has five inspections and one rework event. Events are assertions;
   ordinals are not a live clock and no repair or scrap action is performed.
8. **Yield:** pass the exact selected history dispositions to the same four-unit
   cohort. Conflicting selections withhold counts. Reconciled counts are
   `4 = 2 first-pass + 1 reworked + 1 scrap`, with first-pass fraction `1/2`,
   eventual good `3/4` and scrap `1/4`. The separate pending variant retains its
   four-unit denominator and a pending fraction of `1/4`. No yield target is judged.

The mapping from kits/material declarations to the four named specimens is an
authored fictional example. Matching quantities or hashes does not prove physical
genealogy, actual component consumption, production completion or acceptance.
No latest revision, substitute, workflow policy or real-world authority is inferred.

## Inspect the result

The runner prints `status: PASS`, `command_checks: 24`,
`expected_review_outcomes: 13`, and `operator_review: REQUIRED`.
PASS means all expected checks were reproduced, including the deliberate exit-1
reviews. Some retained complete reports correctly remain REVIEW_REQUIRED.

The fresh private directory contains 24 original inputs, 24 exact CLI reports,
`authored-mapping.json` and `observed-results.json`. Receipts preserve each exit
code and input/report SHA-256. The mapping records report pins and selected cohort;
the summary pins that mapping. Independently recompute a selected file's SHA-256
and compare its receipt. Re-running against the same directory must be refused.
Keep actual operational inputs, reports and logs private; this is not a redactor.

## Contribution and design judgment

This public example composes eight existing independent tools through a newly
authored runner, explicit report mappings, expected refusals and independent
arithmetic checks. The consequential choices are to count canonical lots once,
derive material demand only from selected BOM leaves, keep complete coverage
separate from passing outcomes, and hand over one explicit disposition per specimen.
That makes each check inspectable while leaving each tool's authority limits visible.
The example and implementation were developed with AI assistance; no private
manufacturing workflow or individual operational outcome is claimed.

## Status and verification boundary

This is a runnable source demonstration. Package tests run the actual eight CLI
programs from a fresh complete ZIP, independently rehash retained receipts, check
arithmetic and refuse reuse without mutation. Hosted qualification and public
download verification run the exercise on Windows and Linux; use the release CI
and portfolio evidence for actual observed results rather than inferring success
from these requirements. There is no GUI screenshot claim for this CLI workflow.
Earlier source releases and separate Windows bundles retain their own evidence.

No real orders, reservations, transfers, stock changes, inspections, rework,
physical traceability, quality certification, production decisions or publication
permission are established. A declared successful result remains subject to human
review and independent verification in any actual operating environment.
