# Build two fictional documents from pinned template revisions

Use the complete Toolkit 0.5.0 source package and Python 3.12/3.13. The application
uses SQLite and a constrained standard-library DOCX writer. Word, LibreOffice and
python-docx are not runtime requirements. No runtime is bundled in the Toolkit.

From the extracted complete-package root, choose a new absolute scratch directory
whose parent already exists, outside the package:

```text
python -B workshops/system_exercises.py --exercise documents --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

The runner saves an invented template, previews the selected summary/items sections,
refuses an unreviewed build, and builds a fresh document after explicit review. It
then saves a second immutable revision with a changed heading, includes the optional
review notes, and builds a second fresh document. The original document is preserved.

| Check | Expected result |
| --- | --- |
| Template revisions / previews / documents | 2 / 2 / 2 |
| Item rows | Sample bracket, quantity 3; Example cable, quantity 4 |
| Total quantity | 7 |
| First document | Requested items heading; review notes omitted |
| Second document | Requested quantities heading; review notes included |
| Unreviewed build | REVIEW_REQUIRED; no document created |
| DOCX parts | 8 known XML/relationship parts |
| External relationships / macros | 0 / 0 |
| Original document and selected input bytes | Unchanged |

The runner independently reads each DOCX ZIP and XML to check actual text, table
values and section selection. It does not use the application's own DOCX inspector
as its only oracle. The two DOCX hashes appear in the result. Private outputs are
under `documents/builds/<id>/document.docx`; keep the whole instance private.

Open both generated documents in your intended viewer. Confirm the title, wording,
two item rows, quantity total, section selection and page layout. Automated XML
inspection establishes document content, not visual pagination. The Toolkit's
Ubuntu qualification separately renders these two exact exercise documents using
LibreOffice/Poppler and records page images. That is not Microsoft Word visual proof.

The app executes no template expressions and reads no incoming DOCX files. This
exercise demonstrates versioned composition, explicit review and preservation of
historical output. It does not establish document correctness for future values,
availability or authorization of requested items, private-content clearance, or
identical layout in every viewer. See the [pinned application guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/9a1b5641444888e87dd43ec8d1adfd0faf712d71/systems/document-template-workbench/README.md).
