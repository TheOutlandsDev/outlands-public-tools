# OUTLANDS | Ingestion Receipt Reconciler

Recompute public intake and reconcile pinned previews and row accounting. Independent CLI/library; Python 3.12/3.13 standard-library runtime,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional walkthrough

From this tool's directory:

```text
python -B receipts.py --receipt examples/receipt.json --source examples/source.txt --mapping examples/mapping.json --preview examples/preview.json
```

The invented example returns PASS/exit 0. Source texts and JSON fixtures are
synthetic, with fixed invented identifiers and dates; no private original code,
records, templates, source mappings, operational configuration, user data, paths,
credentials or third-party assets are included. Original applications are not
opened, imported, modified or executed. Combined packages/browser apps are deferred.


## Recomputed intake and receipt comparison

Library: `receipts.reconcile(receipt_raw, source_raw, mapping_raw, preview_raw)`.
The exact receipt format is `outlands-ingestion-receipt-v1` with receipt ID,
source/mapping/preview SHA-256 pins, `source_format` (csv/xlsx), `sheet` and `counts`.
CSV requires sheet null; XLSX requires an exact selected sheet name. Counts are
`input_rows`, `accepted_records`, `duplicate_rows`, `rejected_rows`, `conflict_rows`;
each exact integer 0..1000, excluding booleans. Input rows must equal their four
outcome categories. These are logical data rows, not physical text-line counts.

The tool reruns the byte-identical public Workbook & CSV Intake Checker parser
on the selected source and explicit map. This preserves its typed conversions,
identity grouping, duplicate/conflict treatment, limits and narrow XLSX subset.
The included mapping uses invented Record/Units columns. Refer to intake.py for
the complete public map/parser contract. The source extension is not guessed.
The parser supports bounded plain-cell XLSX only; formulas, hidden/merged cells,
external relationships, macros, unsupported parts/features and expansion excess
are refused. The included public fictional_workbook.py generates invented XLSX
bytes for tests; no binary workbook or original document is bundled.

Receipt pins are compared with the actual raw selections. Supplied preview JSON
must match the recomputed preview as **canonical typed JSON**, including accepted
values, source-row provenance, issue list and flags. Python bool/int equality is
not used for this comparison. Whitespace-only JSON reserialization can match
semantically with an updated raw preview pin; both supplied and recomputed pins
remain in the report. Unknown fields, altered values, missing rows and forged
accounting cannot qualify by changing totals alone.

The output exposes recomputed counts, pins, intake status and fixed issue codes,
without accepted body values or row-level provenance. Rejections, conflicting
identities, empty accepted sets or any receipt mismatch withhold readiness.
`ready_for_explicit_review` is a review gate, not an import, source-authority
check or rights/privacy approval. No store is opened and no source is modified.
Supplied preview values can be private even though this summary omits them.


## Shared limits, I/O and privacy

At most 16 selected artifacts, 4 MiB each and 16 MiB combined. IDs match
`[a-z][a-z0-9_-]{0,47}`; hashes are lowercase SHA-256. Manifest declared totals
also cannot exceed 16 MiB. JSON refuses duplicate keys, floats, nonfinite numbers,
invalid Unicode, excess depth (32)/nodes (100,000), strings over 4,096 characters,
integers beyond the supported bounds and unknown contract fields.

CLIs read explicit regular single-link files using the pinned public Windows/POSIX
guards. No path is read from a manifest, review, receipt or artifact body. Use
trusted quiescent files/parents. Selections are sequential bounded snapshots,
not an atomic capture or a guarantee against a hostile/privileged filesystem.
See [I/O boundaries](IO-SAFETY.md), [origins](ORIGINS.md), [validation](VALIDATION.md).

Output is private ASCII JSON on stdout, or `--out` creates a **new external report**
under an existing parent. Source-tree output and overwrite are refused; no
directory is created. Failed writes can retain partial/unconfirmed output. No
automatic cleanup or same-path retry; choose a new path after private inspection.
Windows inherits parent ACLs, without a confidentiality guarantee. Shell stdout
redirection does not inherit these guards. Reports, symbolic IDs, public-name
proposals, counts, hashes and relationships can still disclose private information.
Hash agreement and path omission do not anonymize an artifact or authorize sharing.

Exit codes: 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Errors
omit supplied values and paths. No source/environment discovery, live query,
process execution or target action occurs. Read each tool's specific evidence
limits above. Parser bounds are not OS resource quotas or an execution sandbox.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
