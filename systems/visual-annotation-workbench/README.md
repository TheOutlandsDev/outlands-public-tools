# Visual Dataset & Annotation Workbench

A complete local application for image review and polygon annotation: canvas editing, immutable proposal/correction lineage, versioned review, specimen-level train/validation/test partitions, independent binary class masks, geometry agreement, checked exports and database backups.

The runtime uses the Python standard library only. Validation targets are Windows x64 and Ubuntu x86_64 with CPython 3.12/3.13. The optional browser acceptance suite separately installs hash-pinned Playwright dependencies and paired Chromium. No browser, photographs, model or private dataset is bundled.

## Start with fictional pixels

Run from this directory using a fresh private workspace outside the source checkout. It must not exist for `init` or `demo`.

```sh
python -B workbench.py --workspace ../fictional-visual-instance demo
python -B workbench.py --workspace ../fictional-visual-instance serve
```

Open the printed loopback URL in a local browser. The demo generates six invented specimens with two views each: three training, one validation and two test specimens. It creates proposals, corrected overlapping regions, four-check approvals, six-view training and six-view evaluation exports, and a database-only backup. First-class agreement is `1209/1351`, comparing fictional polygons, not a model.

For a blank instance use `init`. Create a dataset in the expandable form, place a supported PNG inside its private `inbox`, then import a relative path and proposal. [Example configuration](examples/sample-dataset.json) and [view request](examples/sample-view.json) are templates; the latter requires a separately supplied image. The demo generates its own images without downloading anything.

## Editor workflow

1. Select a dataset and specimen/view. Choose a class and click pixel-edge vertices; press Enter or **Finish polygon**. Class regions can overlap; empty class lists are valid.
2. **Move vertex** drags a vertex. **Pan view**, scrollbars and zoom navigate the image. Coordinate inputs support keyboard drawing; JSON coordinates support precise editing.
3. Undo/redo changes, then save an immutable correction. Invalid or stale saves retain the draft. Save or explicitly reload before switching views. Reload discards the draft. Finish or cancel unfinished vertices before saving.
4. Review the saved correction. Approval requires quality, privacy, rights and context checks. A later correction starts pending. Reviewer aliases and notes are local assertions without authentication or independent verification.
5. Select approved training views explicitly. Held-out views cannot be selected for training. Export approved latest training selections or approved latest validation/test views separately.

Keyboard: Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Ctrl+Y redo; Enter finishes when the canvas is focused; Escape cancels unfinished points. Inputs retain native text shortcuts. Undo history is bounded and disappears on reload.

## CLI and private recovery

```sh
python -B workbench.py --workspace ../fictional-visual-instance list
python -B workbench.py --workspace ../fictional-visual-instance views --dataset sample-visual
python -B workbench.py --workspace ../fictional-visual-instance export --dataset sample-visual --mode training
python -B workbench.py --workspace ../fictional-visual-instance backup
```

Other commands: `create`, `add-view`, `correct`, `review` read an explicit `--file` inside the workspace. `show`, `history`, `evaluate` take `--dataset`, `--specimen`, `--view`; `show` optionally takes `--version`.

Stop the local server before using another command on that instance. An interrupted process may leave an empty session marker. Only after independently stopping every process using the workspace:

```sh
python -B workbench.py --workspace ../fictional-visual-instance recover --confirm-stopped
```

Recovery removes only a verified empty marker; it does not replay work or repair damage. Backups contain the database only. Retain the entire workspace, including canonical images, for complete recovery. Schema validation does not establish authenticity or hostile-database safety.

## Limits and privacy

- PNG subset: non-interlaced 8-bit grayscale/RGB/RGBA, at most 1024 pixels per dimension, 262144 total pixels and 4 MiB input. Palette, 16-bit, APNG and `tRNS` transparency are refused. Canonical RGBA omits ancillary metadata and retains decoded sample values; color-profile/gamma interpretation is not preserved. Visible content and pixels can still identify people or places.
- Integer pixel-edge simple polygons, 3–64 vertices, four polygons per class, 16 total, eight classes. Masks are independent opaque RGBA with 0/255 channels, sampled at pixel centers. No holes, brush painting or class exclusivity.
- Maximum 50 datasets, 64 views per dataset, 200 annotation versions per view, 5000 review records, 64 MiB database and 64 MiB export payload. Database-budget failure rolls back. Failed imports/exports can retain orphan images or partial reports for manual review; no automatic purge.
- One trusted local operator/filesystem. Loopback, Host/Origin checks, session token, no-store and native Windows/POSIX guards are not multiuser authorization or a hostile-local-user boundary. Source/Git output, reparse/symlink/hardlink targets and replacement outputs are refused within the documented helper boundary.
- No trained inference, neural training, medical interpretation, deployment integration or automatic public upload. Future images, identifiers, original-file hashes, notes, masks, exports and backups remain private and require separate review. Removing PNG metadata is not anonymization or permission to publish.

Read [contracts](docs/CONTRACT.md), [design](docs/DESIGN.md), [origins](docs/ORIGINS.md) and [validation](docs/VALIDATION.md). [MIT](LICENSE), copyright TheOutlandsDev. [Collection index](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/systems).

## Checks and source package

```sh
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../visual-annotation-workbench-source.zip
```

Create and activate a separate test venv using your platform's instructions. Then:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Ubuntu may require system libraries: `python -m playwright install --with-deps chromium`. Installation uses network access; application/demo tests need no external service. Browser tests start their own fresh local server and refuse external requests. CI requires native link fixtures and browser interaction on both platforms. Skips are not passes. The source manifest pins selected files except itself; deterministic packaging includes it and refuses existing output.
