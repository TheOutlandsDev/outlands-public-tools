# Offline Environment & Setup Workbench

A complete local CLI/browser application for versioned setup profiles, supplied-observation checks, dependency planning, comparisons, reviewed private plans and evidence handoffs. Python 3.12/3.13 standard library and SQLite; Windows x64 and Ubuntu x86_64. MIT, copyright TheOutlandsDev.

**Plan-only.** No installation, shell command generation, target execution, service launch, DNS lookup, network probe, host inventory, filesystem discovery or configuration change is performed. The optional UI listens only on loopback. A present prerequisite is an operator declaration, not a measured file or executable check. A satisfied contract does not establish runtime readiness.

## Start a complete fictional workflow

First define `$privateWork` as an existing **absolute private directory outside the entire source checkout**. In PowerShell use a string variable; in a POSIX shell use a shell variable. Keep input files and generated instances there. Paths with `..`, UNC names, Windows stream selectors or unsafe/link parents are refused. The instance below must not exist:

```text
python -B workbench.py --workspace "$privateWork/setup-demo-001" demo
python -B workbench.py --workspace "$privateWork/setup-demo-001" serve
```

Open the printed loopback URL. The demo saves two profile revisions, evaluates a missing prerequisite and then a complete supplied declaration, compares the results, saves a reviewed historical plan, exports a private checksummed handoff and verifies an index backup. Expected: 9 checks, 3 blocked steps before, 0 afterward, 2 profiles, 2 evaluations, 1 plan, 10 journal events, 6 handoff files. Only `prerequisite:sample_runtime` changes. No setup actions are performed.

For a blank instance, choose a different fresh destination:

```text
python -B workbench.py --workspace "$privateWork/setup-empty-001" init
python -B workbench.py --workspace "$privateWork/setup-empty-001" serve
```

Initialization copies two fictional JSON examples into the private inbox and seeds the browser editors. Neither editor is saved as a profile/evaluation automatically.

## Complete browser workflow

1. Edit strict profile JSON and save a new revision. Select an existing saved revision as its parent, or choose a new independent profile. **Load saved revision** explicitly replaces the profile editor; supplied observations remain unchanged. Saving always creates a fresh immutable identity, even for identical content.
2. Supply prerequisite assertions, flat settings and portable relative filenames. Save a pinned evaluation against the loaded/saved profile. Edits invalidate evaluation pins and review assertions. Profile edits also disable evaluation until the new revision is saved or a saved revision loaded.
3. Inspect the check table and ordered manual checkpoints. Missing/unknown/unsafe prerequisites, invalid settings, missing names and conflicting declared bindings remain distinct. Blocked dependencies propagate. Optional unresolved prerequisites are counted; any unresolved check explicitly referenced by a step blocks that step.
4. Compare saved profiles or evaluation results. Comparison reports changed identifiers and hashes, not setting values. Inspect a historical evaluation explicitly to create a plan against its original profile; newer revisions never replace its pins.
5. Assert quality/privacy/rights/context review and save a reviewed plan. Plans may retain blockers. Manual verification stays `NOT_PERFORMED`; neither review nor a passing declaration authorizes execution or publication.
6. Inspect the saved plan, assert review again and export a private handoff. The manifest pins five files; `manifest.json` is the sixth file and is written last. Exports contain private profiles, notes and the full journal, including settings. Store them privately.
7. Inspect private history or back up the index. An index backup contains input requests but omits profile/evaluation/plan files, inbox and handoff directories. It is not a complete instance backup. Preserve the whole stopped instance separately when needed.

The UI never renders supplied markup; it uses text nodes. Conflicting controls are disabled during requests. Failed/stale saves retain editor/reason drafts. A lost response triggers no automatic retry: reload the journal and inspect history before deciding whether another operation is needed. Reloading keeps editor text but invalidates loaded pins. Drafts are browser memory and are not backed up. Explicitly loading a revision discards the current profile draft.

## File-based CLI

Stop the server before another CLI process uses the same instance. Save a strict request JSON file inside `inbox`; values stay out of process arguments. See [contract](docs/CONTRACT.md) for the exact envelopes and schemas.

```text
python -B workbench.py --workspace "$privateWork/setup-empty-001" overview
python -B workbench.py --workspace "$privateWork/setup-empty-001" save-profile --file inbox/profile-request.json
python -B workbench.py --workspace "$privateWork/setup-empty-001" evaluate --file inbox/evaluation-request.json
python -B workbench.py --workspace "$privateWork/setup-empty-001" make-plan --file inbox/plan-request.json
python -B workbench.py --workspace "$privateWork/setup-empty-001" history
python -B workbench.py --workspace "$privateWork/setup-empty-001" backup-index
```

The request files above must be created by the operator; only `profile.json` and `observations.json` are seeded. Obtain the current `head` and returned IDs/hashes from each previous result. `inspect --kind profile|evaluation|plan --id ID`, `compare --kind profile|evaluation --first ID --second ID` and `export --file inbox/export-request.json` complete the CLI workflow.

After a crash, independently stop every process using the instance, inspect retained files, then:

```text
python -B workbench.py --workspace "$privateWork/setup-empty-001" recover --confirm-stopped
```

Recovery removes only an unchanged empty stale session directory and marks pending attempts interrupted. It does not replay, resume, repair, delete, adopt partial files or recover lost editor drafts. Failed/partial outputs are retained. Artifact files require matching completed typed journal entries; a marker alone is insufficient.

## Check and package source

```text
python -B run_checks.py
python -B release_source.py check
python -B release_source.py package --output "$privateWork/environment-setup-workbench-source.zip"
```

Output must be new and outside the checkout. `SOURCE-MANIFEST.json` covers the exact source inventory; the deterministic ZIP includes that manifest. Optional browser tests require the separately hash-pinned packages in `requirements-browser.txt`, paired Playwright Chromium and platform dependencies, then `python -B run_browser_checks.py`. Native Windows junction tests require separately supplied PowerShell 7. Set `OUTLANDS_TEST_TEMP` to a suitable existing private test parent. CI requires all seven native link cases; only the opposite-platform case is skipped there. See [validation](docs/VALIDATION.md), [safety](docs/SAFETY.md) and [origins](docs/ORIGINS.md).

This is fresh neutral code using existing public first-party components and fictional fixtures. Original setup scripts, private code, deployment profiles, identities, keys, host details, endpoints, actual records and third-party assets are excluded. Future operator inputs and exports can still contain sensitive information. Value-free check results and neutral source metadata do not anonymize profiles, notes, IDs, hashes or journal data.
