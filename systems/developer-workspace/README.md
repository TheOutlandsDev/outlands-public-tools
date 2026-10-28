# Offline Developer Workspace & Validation Workbench

A complete local browser/CLI application for explicitly supplied text projects: private import, file browsing/editing, immutable revisions, nonexecuting validation, revision comparison, optimistic review, source exports and database backups. MIT, copyright TheOutlandsDev.

The extension-based validator and explicit editor draft/save boundaries adapt selected owner-authored IDE code. The private runtime, neutral contract, store, worker coordination and browser interface use reviewed public first-party patterns and fresh implementation. Original projects, business rules, service launchers, assistant histories, runtime discovery, credentials, operating configuration and records are excluded. See [origins](docs/ORIGINS.md).

## Start a complete fictional project

CPython 3.12/3.13 standard library with SQLite; Windows x64 and Ubuntu x86_64. No Qt, Node.js, model, database server or external service is needed.

From this source directory, choose a fresh private path outside the checkout. It must not exist for `init` or `demo`:

```sh
python -B workbench.py --workspace ../fictional-developer-instance demo
python -B workbench.py --workspace ../fictional-developer-instance serve
```

Open the printed loopback URL. The demo imports five invented files, validates four formats and explicitly leaves Markdown unchecked, edits one file into revision 2, compares source hashes, validates again, approves revision 1's check, exports that historical revision privately and verifies a state backup. Both checks have distinct identities and review state. No supplied Python/JavaScript/SQL/HTML code is executed or rendered; no external service is contacted.

For an empty instance, use `init`, then `serve`. Initialization copies a fictional project bundle to the private inbox. It never scans a real project directory, imports a module or installs a project's dependencies.

## Complete browser workflow

1. Load/paste a neutral JSON project or copy one explicitly into the inbox. Import creates private immutable revision 1. The file list shows only the supplied portable relative paths; the identity panel pins its revision/hash.
2. Select a file and edit its text. Save creates a new full-project revision if content changed. A new path adds a file; renaming requires explicit add and delete. Deletion requires a second confirmation and retains prior revisions. The final file cannot be deleted.
3. Unsaved editor drafts block file/project/revision changes, validation and forks. Use **Discard editor draft and reload latest** explicitly to discard. Conflicting actions are disabled during requests; a stale save is refused with the draft retained. Save and selection operations briefly lock the editor to prevent delayed responses replacing a new draft.
4. Validate the selected saved revision. Only the latest saved hash can start a check. An owned child parses the captured text, with explicit cancel and parent timeout. Editing a draft during validation does not change the captured source. Completion selects its validation and resets the review form; it does not replace the editor draft.
5. Inspect per-file status and coverage. Approve only a completed check with no failures, after all four quality/privacy/rights/context assertions. Unchecked text requires manual review; passing syntax does not prove program behavior. Reviewer labels are local assertions, not authenticated identity.
6. Export approved source **inside the private workspace**. The export pins the validated revision, even when a newer revision exists. New validation runs always start pending, including identical checks. Rejection revokes future exports; it cannot retract files already exported.
7. Compare saved revisions using full-file hashes and bounded unified-diff previews. Load history or fork a saved revision into a new project ID. A historical revision cannot silently overwrite or validate as the latest revision.

Source is always displayed through text fields, never inserted as markup or rendered in a preview. Selection/completion replaces the validation's review form; unsaved review notes are not automatically preserved when changing artifacts. Conflicting review saves retain the current note. Editor drafts and unsaved notes are browser memory, not database backups.

## File-based CLI

Stop the server before another CLI command uses the same instance. For an initialized blank instance:

```sh
python -B workbench.py --workspace ../fictional-developer-instance import --file inbox/sample-project.json
python -B workbench.py --workspace ../fictional-developer-instance projects
python -B workbench.py --workspace ../fictional-developer-instance show --project sample-project
python -B workbench.py --workspace ../fictional-developer-instance history --project sample-project
python -B workbench.py --workspace ../fictional-developer-instance compare --project sample-project --left 1 --right 2
python -B workbench.py --workspace ../fictional-developer-instance artifacts
python -B workbench.py --workspace ../fictional-developer-instance backup
```

The compare command needs two saved revisions; an untouched blank import has only revision 1. `edit --file`, `validate --file` and `review --file` read explicit JSON requests inside the private instance. [Contracts and examples](docs/CONTRACT.md) give every field. `artifact --id` inspects a returned validation ID; `export --artifact` writes the approved source package. Values stay in request files rather than process arguments. Reimporting an identical latest definition is idempotent; a conflicting project ID is refused. Change the bundle's ID to fork.

After an interrupted process, independently stop every process using the workspace before:

```sh
python -B workbench.py --workspace ../fictional-developer-instance recover --confirm-stopped
```

Recovery removes only a checked empty session marker; it does not repair stores or replay checks. Normal shutdown cancels/reaps owned work. Hard parent termination, active-write crash durability and complete restoration are outside acceptance. State backups contain project text, revisions, checks and reviews; they omit inbox files and exported packages.

## Checks and limits

- Python: `ast.parse` only, with a 10000-node limit. No project imports, compilation cache, tests, type/lint checks, dependency installation or runtime execution.
- JSON: bounded strict syntax, duplicate-key and nonfinite-number rejection; not application-schema validation.
- XML/RDL: bounded syntax, DTD/entity refusal, at most 5000 elements, depth 40 and bounded attributes/text. No report schema/layout validation, external resolution or rendering.
- SQL: unchanged public conservative SELECT/CTE preflight, not full parsing, database authorization or execution. Valid queries can be refused; successful preflight is not a security clearance.
- Markdown, text, JavaScript, HTML and CSS: retained as text and explicitly **unchecked**. Browser script/markup is never run. Only declared suffixes are accepted; this is not a complete IDE.
- Projects: at most 200 files, 64 KiB UTF-8 per file and 1 MiB total text. Portable relative paths, no hidden segments, unsafe Windows names, binary/database files, case collisions or file/directory collisions. Excluded directory names are documented in the contract; this is not universal secret detection.
- Store: 40 projects, 100 revisions/project, 400 validation artifacts, 5000 review records, 64 MiB database budget. Requests/source packages are bounded by guarded 4 MiB I/O. Worker result limit 1 MiB, two-second between-file checks and four-second parent kill/reap. No OS sandbox or total process-memory quota is claimed.
- Comparison: all source hashes, at most ten text previews; each side is clipped to its first 200 lines/8000 characters and output to 16000 characters. Omitted/truncated previews remain explicit; a changed file can have an empty clipped preview.

Future source text/comments, filenames, notes, hashes and exports can disclose people, credentials or operations. They remain private. Approval is not publication permission or an anonymization guarantee. Use a separate exact-file content/rights review before sharing an export. [Design](docs/DESIGN.md), [validation](docs/VALIDATION.md), [MIT license](LICENSE).

## Validate and package this application's source

```sh
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../developer-workspace-source.zip
```

Browser acceptance installs separately into a development environment:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Ubuntu may need `python -m playwright install --with-deps chromium`. Test dependencies use network access; application workflows need no external service. CI requires native link fixtures and actual Chromium workflows on Windows/Ubuntu Python 3.12/3.13. Focused release archives contain only manifest-pinned application text; private stores, exports, screenshots, dependencies and browser binaries are excluded.
