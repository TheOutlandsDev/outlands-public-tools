# Batch 96: HTML table and Kanban contracts

Four independent MIT source tools add bounded offline HTML table grid extraction, pinned grid comparison, declared Kanban board validation, and one-move previews. Each directory is independently runnable with only Python 3.12/3.13 standard-library code and fictional examples.

The HTML parser accepts only `table`, `tr`, `td`, and `th` with cell spans. It does not execute scripts or render CSS. The Kanban tools consume caller-supplied symbolic board declarations; they do not connect to or modify a live board. Reports can expose supplied text or IDs and should stay private.

The new tools were authored from generic concepts. No original private implementation, business report, board data, third-party parser or asset was selected. Source manifests pin each complete directory. The repository catalog and GitHub About description are checked together in CI. Combined packaging and clearance of the original private families remain separate review work.
