# Offline Document & Template Workbench

A complete local CLI/browser application for immutable template revisions, strict
typed values, selectable sections, structured item tables, quantity summaries,
pinned semantic previews, fresh DOCX builds and reviewed private handoffs. MIT,
copyright TheOutlandsDev. Python 3.12/3.13 and SQLite; standard-library runtime.
The constrained OOXML writer does not require python-docx, Word or LibreOffice.
Optional Chromium and Ubuntu LibreOffice/Poppler tests are supplied separately.

No original operational template, document, price, customer data, branding, logo,
private path, credential or third-party asset is included. Examples are invented.
This is not a general Markdown/HTML converter, incoming DOCX editor, spreadsheet,
mail-merge service or executable template engine. Read the [contracts](docs/CONTRACT.md),
[safety](docs/SAFETY.md), [origins](docs/ORIGINS.md) and [validation](docs/VALIDATION.md).

## Try the complete fictional workflow

Extract the focused source ZIP and open a terminal in its application directory.
Use fresh private sibling directories outside source control. Literal parent
segments are refused, so construct absolute sibling paths before running commands.

PowerShell:

```text
$documentParent = Split-Path -Parent (Get-Location).Path
$documentDemo = Join-Path $documentParent 'private-document-demo'
$documentPrivate = Join-Path $documentParent 'private-document-ui'
$documentArchive = Join-Path $documentParent 'document-rebuilt-source.zip'
python -B workbench.py --workspace "$documentDemo" demo
python -B workbench.py --workspace "$documentPrivate" init
python -B workbench.py --workspace "$documentPrivate" serve
```

Ubuntu shell:

```text
documentParent="$(dirname "$PWD")"
documentDemo="$documentParent/private-document-demo"
documentPrivate="$documentParent/private-document-ui"
documentArchive="$documentParent/document-rebuilt-source.zip"
python -B workbench.py --workspace "$documentDemo" demo
python -B workbench.py --workspace "$documentPrivate" init
python -B workbench.py --workspace "$documentPrivate" serve
```

The demo saves two template revisions, compares their item-section heading,
composes two pinned previews, builds two fresh DOCX files and exports a nine-file
private handoff. The first preview has two sections, one two-row table and total
quantity seven; the second includes review notes and the revised heading. Twelve
journal events record six completed attempts. The index backup is verified.

Open the printed ephemeral loopback URL on the same computer. Save the fictional
template, edit values, select sections and create a pinned preview. Inspect its
wording, tables and totals, make the explicit review assertions and build a fresh
DOCX. Verify or download the registered document, or export a reviewed private
handoff. Use **Stop local server** before CLI access to that instance.

The browser preview represents semantic text and tables, not Word pagination or
a pixel rendering of the DOCX. Viewer layout, font substitution and future input
lengths can differ. Render and review documents in the intended viewer before use.
Recorded Ubuntu LibreOffice qualification covers fictional short and multipage
examples; Microsoft Word visual rendering is not established by these checks.

## Template revisions and values

Templates use an exact JSON schema with a label, title, declared fields and ordered
sections. Fields are literal text, nonnegative integer quantities or row collections
with explicit typed columns. Scalar substitution uses only `{{field_name}}`; no
expressions, attribute/index lookups, includes, HTML, remote assets or recursive
substitution are evaluated. Values containing template-like or markup characters
remain literal text. All declared values must be supplied, including fields used
only in sections omitted from the resulting document.

Sections declare stable IDs, headings, optional flags and paragraph, bullet or
table blocks. Required sections must be selected; optional sections can be omitted.
Template order controls output order. Table columns have declared widths totaling
100 percent and may summarize explicit quantity columns. Quantities are bounded
integers; totals are transparent sums, not availability, pricing or procurement
assurance. Tables are intended for compact repeated records, not long prose.

Saving a revision always creates a new ID and artifact. Its optional parent must
be an existing revision. Comparison reports added/removed/changed fields and sections,
ordering and title/label changes. Old revisions and previews are preserved; editor
changes require a new saved revision/preview. Building a historical preview uses
that exact retained template and values, not the current editor draft.

## CLI requests and artifacts

```text
python -B workbench.py --workspace "$documentPrivate" overview
python -B workbench.py --workspace "$documentPrivate" save-template --file inbox/template-request.json
python -B workbench.py --workspace "$documentPrivate" inspect-template --id TEMPLATE_ID
python -B workbench.py --workspace "$documentPrivate" compare --first FIRST_ID --second SECOND_ID
python -B workbench.py --workspace "$documentPrivate" preview --file inbox/preview-request.json
python -B workbench.py --workspace "$documentPrivate" inspect-preview --id PREVIEW_ID
python -B workbench.py --workspace "$documentPrivate" build --file inbox/build-request.json
python -B workbench.py --workspace "$documentPrivate" inspect-build --id BUILD_ID
python -B workbench.py --workspace "$documentPrivate" export --file inbox/export-review.json
python -B workbench.py --workspace "$documentPrivate" history
python -B workbench.py --workspace "$documentPrivate" backup-index
```

The seeded template request is valid only for an empty journal. Every mutation
request has `expected_head`, `actor`, `reason`, `request`; use the current head from
`overview` or the previous successful response. Template request data contains
`parent_id` (nullable) and `template`. Preview data contains `template_id`, its exact
`template_sha256`, typed `values` and selected section IDs in `sections`.
Build request data is:

```json
{
  "preview_id": "REPLACE_WITH_REVIEWED_PREVIEW_ID",
  "preview_sha256": "REPLACE_WITH_RETAINED_PREVIEW_HASH",
  "checks": {"quality": true, "privacy": true, "rights": true, "context": true}
}
```

The placeholder strings are not valid IDs/hashes. Use the inspected saved preview's
actual values. All checks must be exact true Booleans. Actor, reason and checks are
private operator assertions; they do not prove identity, factual correctness, rights,
anonymization or publication permission. See the [exact contract](docs/CONTRACT.md).

Instances contain `workspace.json`, `inbox/`, `database/`, `templates/`, `previews/`,
`builds/`, `reports/` and `index-backups/`. Template/preview folders have their JSON
artifact and final `READY.json`; build folders contain `document.docx`, retained
`preview.json` and final `BUILT.json`. Final markers and completed journal
registration are both required. Unregistered physical output is never adopted.

## DOCX format and inspection

The writer creates eight known OOXML parts from scratch. There are no incoming
DOCX templates, default-template thumbnails/custom XML, media, macros, external
relationships, fields, embedded objects or fetched resources. Core/application
properties use fixed neutral OUTLANDS values and nonidentifying dates; ZIP member
dates and attributes are fixed. This is a constrained format with explicit
metadata, not a metadata-free or anonymous document guarantee.

Documents use Letter portrait, one-inch margins, Arial 11-point body text, black
titles/headings and dark blue table headers with light gray borders and alternating
body shading. Headers repeat across pages, widths are deliberate and rows have no
fixed heights. Bullet glyphs are literal text. Line endings normalize to LF; line
breaks/tabs become Word break/tab elements. No automatic page fields are emitted.

Build and inspection verify every part against the retained semantic model,
properties, relationships, member metadata and exact document hash. Download uses
a fixed filename and a registered build ID, with verification before serving bytes.
Package/content inspection does not verify facts or viewer pagination. Inputs and
all generated content remain private, including document body text.

## Private handoffs, interruption and limits

Export requests have `expected_head`, `actor`, `reason`, `preview_id`, nullable
`build_id` and the four review checks. A selected build must match the preview and
pass current verification. Handoffs contain template, preview, journal, review,
receipt, inspection and hash manifest, plus DOCX/checksum when selected. They
contain input values and can contain values omitted from the visible document.
The manifest always says `public_release_authorized: false`.

Started attempts are committed before writes. Failures retain partial output.
Interrupted attempts block new jobs. A lost response may already have committed:
reload history and inspect before another deliberate request. The browser never
automatically retries writes. After independently confirming all instance processes
are stopped:

```text
python -B workbench.py --workspace "$documentPrivate" recover --confirm-stopped
```

Recovery clears only an unchanged empty stale lock and records pending attempts as
interrupted. It does not resume, delete, overwrite or adopt anything. Index backups
contain private template/value requests and journal data but omit document artifact
files; they are not complete instance backups. There is no automatic restore,
corruption repair, rollback, cleanup or journal compaction.

Limits: 16 fields, 16 sections, 64 total blocks, eight table columns, 100 rows per
row field and 400 rendered table rows. Quantities are 0 through 999999999. Scalar
text is at most 800 UTF-8 bytes, row text 240 bytes, expanded body blocks 2400 bytes
and expanded titles 200 bytes. Template JSON is at most 64 KiB, value JSON 128 KiB,
preview 256 KiB, DOCX 2 MiB, individual messages/reports 4 MiB and index 64 MiB.
An instance has at most 64 attempts and 256 journal events. These are bounds, not
a global disk quota; repeated reports/backups and retained failures consume space.
Retain capped instances and use a fresh private instance for further work.

## Check and package source

```text
python -B -W error run_checks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install --with-deps chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output "$documentArchive"
```

Optional Ubuntu rendering requires separately installed LibreOffice Writer and
Poppler (`soffice`, `pdfinfo`, `pdftotext`, `pdftoppm`). Choose a new private output
directory outside source control and run `acceptance/render_check.py --output`
with that absolute directory. It generates fictional short/long documents, checks
PDF text/pages and produces page PNGs requiring visual review. Render tooling is
not an application dependency and generated render outputs are not source assets.

The source ZIP contains only inventoried code, docs, tests and invented JSON inputs.
Instances, DOCX/PDF/PNG outputs, logs, reports, original materials and runtime binaries
are excluded. Trusted parents and no hostile concurrent filesystem editor are
assumed. Production suitability, encryption, signatures, atomic live-source capture,
complete disaster recovery, hardware behavior and universal viewer/font fidelity
are not established.
