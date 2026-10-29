# Offline Release & Update Workbench

A complete local CLI/browser application for immutable release snapshots, pinned file/lock comparisons, conservative update plans, scoped approval/revocation, durable history and private evidence handoffs. Python 3.12/3.13 standard library and SQLite; Windows x64 and Ubuntu x86_64. MIT, copyright TheOutlandsDev.

**Target updates stay plan-only.** The application copies explicitly selected inbox packages into new private snapshot directories and writes private workflow artifacts. It never installs a package, executes a payload/launcher, applies/removes target files, starts/stops services, probes networks or discovers a live installation. A captured baseline is a saved package, not proof of a current target or usable backup. Actual application/runtime acceptance is untested.

## Complete fictional workflow

First define `$privateWork` as an existing absolute private directory outside the entire source checkout. Use a PowerShell string variable or a POSIX shell variable. Paths with parent traversal (`..`), unsafe/link/reparse parents, filesystem/share roots or Windows streams are refused. The instance below must not exist:

```text
python -B workbench.py --workspace "$privateWork/release-demo-001" demo
python -B workbench.py --workspace "$privateWork/release-demo-001" serve
```

Open the printed loopback URL. The demo captures two invented four-file packages; compares them with missing assertions and then with explicit operator assertions; saves and approves a manual plan; exports a private handoff; and verifies an index backup. Expected differences: **1 ADD, 1 REMOVE, 2 REPLACE, 1 UNCHANGED**, one declared lock version-text change, five blockers before and zero afterward, two snapshots, two comparisons, one plan, eleven journal events and eight handoff files. Every target checkpoint remains unperformed. The example launcher points at an inert `.txt` payload; listing it does not make it executable or runnable.

For a blank instance use a different fresh destination:

```text
python -B workbench.py --workspace "$privateWork/release-empty-001" init
python -B workbench.py --workspace "$privateWork/release-empty-001" serve
```

Initialization seeds invented inbox packages/requests and the editor examples. No snapshots are registered automatically. Keep all future real inputs, instances and handoffs private.

## Browser workflow

1. Load an invented editor example or supply a strict capture request. It selects an ordinary package directory inside the private inbox and declares its exact manifest, independently trusted canonical manifest digest, optional narrow dependency lock and launcher specification. Capture verifies the selected tree, copies its bytes into a fresh private snapshot, rechecks input/output and registers completion last. Identical explicit captures still get new identities.
2. Select baseline/candidate snapshots. Assert independent backup, consistent stopped target, prerequisite/readiness, omission/removal and dependency reviews where justified. Save a pinned comparison. These are operator assertions, not performed checks. Unknown/unchecked prerequisites remain blockers.
3. Inspect added/replaced/omitted/unchanged files and limited dependency declarations. File/directory or case-only layout transitions remain blocked. A missing candidate file means `REMOVE` in the comparison, not a deletion action. Source extra files/empty directories and pin mismatches are refused during capture.
4. Save a manual plan. Blocked plans can be retained for diagnosis but cannot be approved. Inspect the plan and all upstream snapshot bytes, then assert quality/privacy/rights/context review to approve a private handoff. Approval never executes an update or grants publication permission.
5. Review again and export private evidence. Revoke to block future exports; previously exported files remain outside this app's control. New plans never inherit approval, including plans for identical inputs. Changed snapshot bytes block inspection/approval/export. Editor, policy and selection changes invalidate the browser's loaded pins and review assertions. Explicit historical inspection can still use the original immutable pair and current decision.
6. Inspect private typed history or back up the index. Journal requests contain source selectors, dependency text, launcher arguments and operator notes. Index backups omit payload/artifact files and are not complete instance backups. Preserve a stopped full instance separately if needed.

The UI uses text nodes for supplied content, disables conflicting controls during requests and retains editor/note drafts on refusal. It never retries a write automatically after a lost response: reload and inspect history first. Reload keeps editor text but clears loaded pins. **Load invented request** explicitly replaces the capture editor. Browser drafts are not persisted or backed up. A refresh is not a target drift check.

## File-based CLI

Stop the server before separate CLI use of the same instance. Seeded `inbox/capture-v1.json` has the initial zero head and is ready for the first blank capture:

```text
python -B workbench.py --workspace "$privateWork/release-empty-001" capture --file inbox/capture-v1.json
python -B workbench.py --workspace "$privateWork/release-empty-001" overview
python -B workbench.py --workspace "$privateWork/release-empty-001" history
python -B workbench.py --workspace "$privateWork/release-empty-001" backup-index
```

Subsequent writes need the latest returned `head`; update request files inside the inbox. Optional `parent_id` links a new capture to a registered snapshot. `compare`, `make-plan`, `review` and `export` use `--file inbox/REQUEST.json`. `inspect --kind candidate|comparison|plan --id ID` verifies a registered artifact. Full envelopes and schemas appear in the [contract](docs/CONTRACT.md). Values stay in private files rather than process arguments.

After a crash, independently stop every process using the instance, inspect retained output, then:

```text
python -B workbench.py --workspace "$privateWork/release-empty-001" recover --confirm-stopped
```

Recovery only removes a checked empty stale session directory and marks pending attempts interrupted. It does not replay, resume, repair, delete, adopt orphan output or restore payloads. Files/markers without matching completed journal records are not registered snapshots. Failures and partial output are retained; no existing file is replaced.

## Check and package source

```text
python -B run_checks.py
python -B release_source.py check
python -B release_source.py package --output "$privateWork/release-update-workbench-source.zip"
```

The output must be new and outside the checkout. The pinned inventory covers the exact source files; the deterministic ZIP includes its manifest. Optional browser acceptance uses separately supplied hash-pinned `requirements-browser.txt`, paired Playwright Chromium/platform dependencies, then `python -B run_browser_checks.py`. Native Windows junction tests need PowerShell 7. Set `OUTLANDS_TEST_TEMP` to an existing suitable private test parent. CI requires eight native link/junction fixtures; only the opposite-platform case may be skipped.

Publication includes fresh neutral code, existing public first-party cores and invented fixtures only. Original launchers/updaters, private code, operational configurations, credentials/keys, player/customer records, actual host paths/topology, game/mod assets, runtime binaries, logs and generated artifacts are excluded. Private snapshots and reports are not automatically sanitized. See [safety](docs/SAFETY.md), [origins](docs/ORIGINS.md) and [validation](docs/VALIDATION.md).
