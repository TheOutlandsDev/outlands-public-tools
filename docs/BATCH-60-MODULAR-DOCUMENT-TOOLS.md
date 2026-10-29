# Four independent document intake and reconciliation tools

| Source tool | Scope |
| --- | --- |
| [DOCX Table Extractor](../tools/docx-table-extractor/README.md) | Index stored tables and explicitly select text/table content with provenance |
| [Document Intake Checker](../tools/document-intake-checker/README.md) | Apply caller-declared typed mapping and conserved row accounting to one selected table |
| [Tabular Reconciliation Checker](../tools/tabular-reconciliation-checker/README.md) | Compare explicit typed record identities, changes and exact numeric totals |
| [Document Content Diff](../tools/document-content-diff/README.md) | Compare supported stored paragraph/table blocks by position with input/content hashes |

Each is a separate MIT source directory with a CLI, buffer-based library interface,
fictional examples, tests, source manifest and documented validation/I/O boundaries.
There is no new browser application or combined distribution package. Catalog
family labels support navigation; immutable Toolkit assets and package plans are
unchanged. Packaging remains deferred until the remaining source audit and the
user's additional list are reconciled.

## Source and privacy boundary

Fresh generic code and fictional formats/data. Only the existing public I/O helpers,
source checker/native tests and typed intake core are reused, with exact origin
pins. No private original application code, document/template, business schema,
formula, mapping, customer/user record, operational configuration, credential,
private path, image or third-party asset is selected. Original private applications
are not modified, imported or executed. Whole original-family clearance remains
incomplete. Inventory presence is not clearance to publish.

DOCX archives are never extracted, rendered or executed. Supported main-body text
and rectangular tables are checked; active/unsupported constructs and unsafe OPC
relationships fail closed. Opaque property/format parts are bounded but not exported
or interpreted. Stored text is not an assertion of what Word visibly renders, and
content hashes deliberately exclude formatting/properties. Raw hashes remain
separate. Real document body content, identity fields, hashes and reports stay private;
none of the tools anonymizes a real document or proves authority to share it.

Intake preserves the public type/duplicate/conflict rules. Reconciliation conserves
every input row, withholds all comparison/totals on rejected/conflicting rows and
uses exact declared numeric types. Equal totals alone do not imply matching records.
Document diff uses positional coordinates rather than fuzzy business identity.

## Qualification

[The qualification workflow](../.github/workflows/document-tools-checks.yml) runs
Windows/Ubuntu with Python 3.12/3.13 and no third-party runtime installation. Native
hardlink/junction/symlink fixtures are mandatory; only opposite-platform tests can
be skipped there. Exact source manifests and public predecessor bytes are checked.

Invented package mutations exercise external relationships, active content,
ambiguous tables, malformed archives, XML/expansion limits, preserved text and
property/format exclusions. Actual standalone CLI copies create only fresh private
outputs and refuse overwrite. The collection walkthrough exercises DOCX intake
to explicitly constructed record sets, reconciliation with equal totals but changed
rows, content differences and an independent existing public DOCX writer.

No original document, live service/database, production workflow, general Office
GUI/rendering behavior, hostile filesystem race or power-loss durability is claimed.
Private failure evidence, audit reports and source locations remain outside the
repository. See each tool's README, VALIDATION.md, ORIGINS.md and IO-SAFETY.md.
