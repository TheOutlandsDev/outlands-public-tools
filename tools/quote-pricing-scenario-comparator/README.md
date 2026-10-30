# Quote Pricing Scenario Comparator

Compare one supplied basket cohort under two complete declared price books.

Independent MIT source; Python 3.12/3.13 standard library.

```text
python -B scenarios.py --input examples/input.json
python -B scenarios.py --input examples/needs-review.json
```

Library: `scenarios.check(raw_json_bytes)`. Optional `--out` selects a NEW
absolute private report outside source, beneath an existing trusted parent.

Input exactly `{format,baseline_price_books,candidate_price_books,baskets}`, format `outlands-quote-pricing-scenarios-v1`.
See the exact schemas and scope distinctions below.


## Exact declarations and bounds

All keys below are required; unknown keys, nulls, implicit defaults and unsupported
types are refused. IDs/units are symbolic `[a-z][a-z0-9_-]{0,47}`. Revisions are exact
integers 1..1,000,000, excluding booleans. Each top-level cohort has 1..128 raw rows.
Identical normalized top-level IDs collapse with duplicate accounting; all members
of conflicting IDs are excluded. Any rejected/conflicting row withholds the entire
assessment and all qualified/cohort pins. Nested IDs must be unique even if identical.
No item aliases, name inference, external lookup, scripts or expressions are supported.

Price book exactly `{id,revision,currency,minor_digits,rounding,items}`. Currency is a
three-uppercase-letter declaration, with no lookup or real currency validation.
minor_digits is exact integer 0..4; rounding is half_up, half_even or down. It applies
to nonnegative amounts. Items has 1..256 exact `{id,unit,tiers}` records, normalized
by ID. Each tiers list has 1..16 exact `{minimum_quantity,unit_price}` records. The
first minimum is zero; subsequent minima strictly increase in supplied order. Tier
sorting, overlaps by inferred intervals and gaps before zero are never repaired.
The selected tier has the greatest minimum <= quantity (inclusive). Its unit price
applies to the entire quantity, not progressive bands. No maximum tier is implicit.

Quantities/prices/rates/amounts are decimal STRINGS, never JSON numeric values. Syntax
is nonnegative plain decimal, no plus/minus, exponent, whitespace or leading zeroes
except zero itself; 0..6 fractional digits, at most 19 integer digits. Trailing zeroes
normalize away. Quantity is >0 and <=1,000,000; tier minimum is 0..1,000,000; unit price
is 0..1,000,000,000. Amounts are <=10^18. Rate is 0..1. Zero prices are supported.
Arithmetic uses exact rational/integer operations, independent of Decimal context.
Normalized record SHA-256 is sorted-key compact ASCII JSON plus one LF; use the
normalizer before pinning. Byte hashes and normalized hashes have distinct meanings.

## Line pricing input

Quote exactly `{id,revision,price_book,price_book_revision,price_book_sha256,lines}`.
lines has 1..256 exact `{id,item,unit,quantity,unit_price}` records, normalized by ID.
References bind the complete normalized selected book, including unused items and
rules. Missing/stale references withhold all assessments. Unit must equal the selected
item's symbolic unit exactly; there is no unit conversion. Declared unit price must
equal the selected tier price exactly, before rounding. Each result has fixed state
valid, item_unknown, unit_mismatch or price_mismatch; unavailable prices/extensions
are null. A price mismatch retains the expected price and rounded extension for review.
PASS requires all selected quotes' lines valid. Rounded extension uses expected price,
not an untrusted asserted price. No quote or price book is edited.

## Total reconciliation input

This tool's quote is a separate arithmetic schema, not the line-pricing quote:
`{id,revision,currency,minor_digits,rounding,lines,adjustments}`. Arithmetic lines have
exactly `{id,quantity,unit_price}`, 1..256 records normalized by ID. This tool does not
authenticate prices against a book. Its independent input permits arithmetic review
without requiring another tool. The connected example explicitly projects reviewed
line prices; it does not imply arbitrary callers did so.

Adjustments has 0..32 exact `{id,kind,value}` records with unique IDs. Order is
semantic and preserved in pins. kind is discount_fixed, surcharge_fixed, discount_rate
or surcharge_rate. Fixed values must be exactly representable at minor_digits; rates
are exact fractions of the CURRENT rounded running balance. Each line extension first
rounds independently to minor units; the subtotal sums these rounded extensions. Then
adjustments apply sequentially. Rate magnitudes round with the declared rule before
application; fixed magnitudes are exact. Discounts subtract, surcharges add. Reported
adjustment amounts are nonnegative magnitudes, with effect determined by the pinned
kind. Over-discounts refuse the entire assessment; no clipping or negative totals.
Every subtotal/running balance must stay <=10^18. No rounding at a later aggregate step.

Claim exactly `{id,revision,quote,quote_revision,quote_sha256,line_totals,adjustment_totals,subtotal,total}`.
The quote reference pins the complete normalized arithmetic quote. line_totals contains
0..256 exact `{line,amount}` records; adjustment_totals contains 0..256 exact
`{adjustment,amount}` records. Reference IDs within each list are unique; both lists
normalize by reference ID. Claims must use exact minor-unit precision, with no silent
rounding. The checker separately compares every expected line/adjustment amount, full
coverage, subtotal and total. Missing/unknown IDs and mismatches remain review findings
even if the final total happens to match. Every claim must reconcile for PASS.

## Scenario comparison input

Each side's price-book cohort must normalize to exactly one book. A basket exactly
`{id,revision,lines}` contains 1..256 exact `{id,item,unit,quantity}` records, normalized
by line ID. One shared nonempty basket cohort prevents silently dropped observations.
Price-book IDs may differ. If ID AND revision match but normalized definitions differ,
the scope is structurally inconsistent and all assessment/pins are withheld. A new
revision is required for a changed definition under the same ID. Different currency or
minor_digits withholds comparison; no conversion is inferred. Different rounding rules
are evaluated on the actual baskets. Unknown items or mismatched units on either side
make that basket incomparable and unequal, including equal-looking negative outcomes.

For comparable baskets, equality requires exact selected tier threshold, normalized
unit price and rounded extension equality for every line. Subminor price changes remain
visible even when rounded extensions happen to match. Changes to unused tiers/items
may leave selected outcomes equal. PASS therefore establishes only this supplied basket
cohort's outcomes, never whole-catalog compatibility or equivalence of all definitions.
The report exposes both selected price/extension results. No prices are recommended.

## Reports, errors and evidence limits

Reports contain status PASS or REVIEW_REQUIRED, raw input_sha256, per-cohort accounting,
fixed-code issues, assessment, cohort_sha256 and qualified_scope_sha256. Logical price,
claim or scenario mismatches retain an assessment/cohort pins but withhold qualified
scope. Structural findings withhold assessment and both pins. A qualified scope hash
pins the map of normalized cohort hashes; it is not a signature or approval.
No free-text fields are accepted. Amounts and stable symbolic IDs appear in reports
because they are necessary for arithmetic review. Keep actual inputs/reports private;
hashes do not anonymize data. Malformed-row diagnostics omit supplied values.

CLI exit 0 means PASS, 1 REVIEW_REQUIRED and 2 a fixed-code input/output refusal.
Input <=4 MiB, output <=8 MiB, JSON depth <=32 and <=100,000 nodes. JSON floats,
nonfinite constants, duplicate keys and invalid Unicode are refused. Native file I/O
requires trusted local paths, a single regular input link and fresh private output
outside source; existing/link/ambiguous paths are refused. See [I/O safety](IO-SAFETY.md).
The inherited JSON/I/O code includes additional unused XML helpers; these tools accept
JSON only. Filesystem controls are bounded and are not a hostile-machine guarantee.

These tools only evaluate supplied declarations. No network, dispatch, quote mutation,
store import, model call, invoice, payment, tax determination, identity verification,
signature validation or actual customer approval. Currency and adjustment rules are
caller declarations. No live service, financial correctness beyond the stated arithmetic,
production readiness, browser behavior, privacy or rights clearance follows.
