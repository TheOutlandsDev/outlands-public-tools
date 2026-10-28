# Offline Test & Evidence Workbench

A complete local CLI/browser application for a versioned registry of trusted Python checks, explicit execution trust, pinned run plans, expected/observed results, private evidence, comparisons, review and exports. MIT, copyright TheOutlandsDev.

This selected adaptation retains the owner-authored IDE's owned-process/output/cancel and named-case dashboard methods as design and implementation patterns. The neutral contracts, bounded capture, private store and browser interface are fresh implementation around public first-party I/O/runtime patterns. Original case registries, business checks, queries, credentials, operating settings and real evidence remain excluded. [Origins and rights](docs/ORIGINS.md).

## Execution is explicit trusted code

**An approved check runs Python with the operator's filesystem and network permissions. This is not a sandbox.** Trust only code whose effects you understand and authorize. The application does not contain or terminate descendants, restrict filesystem/network access, or impose a total CPU/memory/disk quota. A check must manage its own descendants. Capture concerns the owned immediate child, not all processes it may create.

Saving/importing a case, inspecting a snapshot or approving trust does not execute it. Each whole case revision needs four explicit trust assertions. Run plans pin the latest case hash and trust version; the complete plan is checked before any child starts. Revocation blocks later plans; it does not cancel an accepted plan or its remaining cases. Use Cancel for active work. Review/export decisions are separate and never authorize execution or change a test verdict.

The application has no live database, report server, model or external-service adapter. The supplied fictional checks use local standard-library code only. Arbitrary trusted Python can use resources outside this application; “offline” is not network isolation. No original operational check is run by this package's examples or tests.

## Start a complete fictional instance

CPython 3.12/3.13 standard library with SQLite; Windows x64 and Ubuntu x86_64. From this source directory choose a fresh private path outside the checkout. It must not exist for `init` or `demo`:

```sh
python -B workbench.py --workspace ../fictional-evidence-instance demo
python -B workbench.py --workspace ../fictional-evidence-instance serve
```

The **demo explicitly executes the supplied fictional Python scripts**. It imports and records trust for four invented cases: a sum, an expected nonzero refusal, a deliberate expected-output mismatch and a deliberate timeout. It records **two matches and two unmatched cases**, then runs the first two again, compares review identities, approves the first artifact as evidence, exports thirteen private files and verifies a database backup. Approval of failure evidence does not make its checks pass.

For an empty store that executes nothing, use `init`, then `serve`. Initialization only copies the fictional case bundle into the private inbox. Open the printed loopback URL. The application is for one trusted local operator, with no authenticated reviewer accounts or remote/multiuser support.

## Browser workflow

1. Import a neutral case bundle or edit a fictional template. Inspect the Python source, input object, expected exit/stdout/stderr and timeout. Save immutable revisions. Change the ID to fork into a new pending-trust case. Historical/stale saves are refused; unsaved drafts block switching, trust and running until saved or explicitly discarded.
2. Review the exact saved source and record code/authority/input/effects trust assertions. Nothing runs during approval. Any change to code, input, expected result, title or timeout creates a new revision requiring fresh trust. Trust conflicts retain the typed note.
3. Select approved cases, build a pinned plan, inspect its IDs/hashes/trust versions, then choose **Run this trusted plan**. Up to eight cases run sequentially in fresh private directories. There is no automatic execution on save, import, startup or recovery, and no automatic retry.
4. Inspect expected versus observed exit code, parsed stdout, stderr and raw-byte capture hashes. Status distinguishes completed, timeout, output-limited, cancelled, refused and not-run. A nonzero exit can match an explicitly expected nonzero exit; a timeout/output cap cannot be a passing check.
5. Review complete evidence with quality/privacy/rights/context assertions. Complete failure evidence may be approved as evidence; cancelled/incomplete evidence cannot. Every run has a separate identity and starts pending, even if the cases and output are identical. Selecting/completing a run replaces its review form; editor drafts remain separate. Unsaved browser notes are not persisted.
6. Export approved evidence **inside the private instance**, compare pinned artifacts and create state backups. New case edits do not rewrite earlier source/output snapshots. Revoking a review blocks future exports but cannot retract files already exported. These actions never publish anything.

Source, stdout and stderr are displayed as literal text, not HTML. Saved-source selection is atomic across case/history requests; a failed fetch cannot rebind the editor. Requests that replace case text briefly lock the editor and conflicting actions. A draft edited during a run remains separate from the captured case revision. Reload/closure may lose unsaved drafts and notes.

## File-based CLI

Stop the server before another CLI command uses the same instance. An empty initialized store accepts the copied fictional bundle:

```sh
python -B workbench.py --workspace ../fictional-evidence-instance import --file inbox/sample-cases.json
python -B workbench.py --workspace ../fictional-evidence-instance cases
python -B workbench.py --workspace ../fictional-evidence-instance show --case sample-total
python -B workbench.py --workspace ../fictional-evidence-instance history --case sample-total
python -B workbench.py --workspace ../fictional-evidence-instance artifacts
python -B workbench.py --workspace ../fictional-evidence-instance backup
```

`save-case --file`, `trust --file`, `run --file` and `review --file` use explicit JSON request files inside the private workspace. [Contracts](docs/CONTRACT.md) define every field. `artifact --id`, `compare --left --right` and `export --artifact` use returned artifact IDs. No executable, command arguments, shell flag, environment mapping or external process ID is accepted by these contracts. The selected interpreter runs only the explicitly trusted staged Python source; that code itself remains powerful.

After interruption, independently stop every process using the workspace before:

```sh
python -B workbench.py --workspace ../fictional-evidence-instance recover --confirm-stopped
```

Recovery removes only a verified empty session marker and replays nothing. Normal shutdown cancels/reaps the owned immediate child. Hard parent termination can leave it or descendants running; active-write crash durability and complete restore are outside acceptance. Backups contain case/trust/evidence/review state, but omit inbox files, run directories and exports. Failed/unconfirmed runs and partial exports remain private for inspection; no cleanup or rerun happens automatically.

## Limits and evidence meaning

- Case: 32 KiB UTF-8 source, 16 KiB input object, 8 KiB expected stdout object, 2 KiB expected stderr, 100–5000 ms timeout, 128 KiB encoded definition. JSON refuses duplicate keys/nonfinite values; nested objects are bounded, numbers within ±1e12 and integral floats normalize to integers. Boolean/number distinctions remain.
- Process: current interpreter with `-I -S -B -X utf8`, no shell or interactive stdin, fresh private working directory and minimal environment. Ordinary caller environment/credentials are not inherited; this does not prevent trusted code reading credentials or starting other processes itself.
- Capture: at most 16 KiB raw bytes per stdout/stderr stream, concurrent byte reads without waiting for a newline. Overflow terminates the owned child and marks capture as a prefix. Invalid UTF-8 retains exact base64/raw hashes plus replacement display text and cannot match the stdout protocol. Stdout must be exactly one bounded JSON object. Stderr compares after CRLF-to-LF normalization; raw bytes never normalize.
- Timeouts measure monitoring after process creation. Operating-system process creation/scheduling and native calls are not hard real-time guarantees. Capture readers stop after the owned child exits; descendant output/cleanup is outside the guarantee.
- Registry/store: 100 case IDs, 100 revisions/case, 20 cases/import, eight cases/plan, 200 evidence artifacts, 5000 trust and 5000 review rows, 64 MiB database, 1600 application-created run directories. Script effects can exceed these local bookkeeping limits. A persistence failure after execution may return `saved:false`; inspect retained runs before deciding what to do next.

Scripts can print false claims, and a matching expected output is not independent proof of a real system's correctness. Source/input hashes identify staged bytes and local assertions, not signed attestations or isolation. Every future script, input, expectation, captured path/secret, note, raw output and export remains private. Review is not anonymization or public-release permission. Perform a separate exact-file privacy/rights review before sharing. [Design](docs/DESIGN.md), [validation](docs/VALIDATION.md), [license](LICENSE).

## Test and package this application's source

```sh
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../test-evidence-workbench-source.zip
```

Browser acceptance installs separately into a development environment:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Ubuntu may need `python -m playwright install --with-deps chromium`. Test installation uses network access; fictional application checks do not. CI requires applicable native link fixtures and actual Chromium workflows on Windows/Ubuntu Python 3.12/3.13. Focused release assets contain only manifest-pinned source text, excluding private stores, run scripts/captures, evidence, screenshots and dependency/browser binaries.
