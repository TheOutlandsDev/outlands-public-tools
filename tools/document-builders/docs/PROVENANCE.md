# Source provenance and preserved behavior

The standalone qualification starts from public collection commit
`f7604b06ffe62f9f6296b745ac4c11c400f6c036`, directory
`tools/document-builders`. This is an existing MIT-selected Markdown builder,
not a new implementation copied from operational documents.

Both runtime files (`markdown_docx.py`, `docx_windows.py`) and the authored
`examples/fictional_request.md` retain the baseline Git bytes. All 72 existing
test method bodies and their helper/assertion contracts are preserved. The
original files comprise 27 regressions in `test_markdown_docx.py` and 45
portable/native cases in `test_docx_windows.py`. The preservation proof binds
actual methods/helpers rather than replacing their expectations with a new
parallel test suite. The source manifest records the selected published bytes.

The source-only qualification adds dependency/hash locks, finite inventory and
packaging helpers, strict native test-loading policy, copied-runtime CLI/package
checks, standalone documentation and release records. It preserves the original
runtime's supported Markdown subset, neutral configured core properties,
exclusive output behavior and distinct platform cleanup policies.

The owner reports personal work created with AI assistance. Parser/layout
helpers were adapted from the owner's builder project; operational covers,
selected-section rules, logos, fixed paths and source records were excluded.
Qualification and publication methods were AI-assisted. Required selected-source
copyright/license notices remain. This bounded review is not independent proof
of exclusive authorship or permission to distribute real documents.

The [historical Windows review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-22-DOCUMENT-BUILDER-WINDOWS.md)
provides earlier platform/package observations. The current standalone
qualification is separate from that review and from the old aggregate Python
3.15 observation. Its exact dependency closure and fresh installs are verified
separately. Older bundles and wheel compatibility declarations are unchanged.

The ZIP does not include third-party implementations, installed runtimes,
wheels, private originals, real document inputs/outputs or raw logs. Source
hash agreement does not establish correctness, authorship, anonymity, licensing
clearance for user inputs or business readiness. Review inherited template
parts and output text before sharing.
