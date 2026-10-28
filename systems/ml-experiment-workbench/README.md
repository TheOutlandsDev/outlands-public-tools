# Offline ML Experiment & Evaluation Workbench

A complete local binary-prediction application: import neutral tabular data, configure chronological experiments, train a logistic baseline, inspect validation-selected thresholds, explicitly record a later holdout evaluation, review immutable artifacts, compare runs and export private models/reports.

Runtime: Python standard library only, CPython 3.12/3.13 on Windows x64 and Ubuntu x86_64. No model service, account, GPU or pretrained weight is required. Optional test-only Playwright dependencies and paired Chromium install separately. This is an inspectable educational baseline, not a production model platform or evidence of real-world accuracy.

## Start a complete fictional instance

From this directory, choose a fresh private workspace outside the source checkout. The path must not exist for `init` or `demo`.

```sh
python -B workbench.py --workspace ../fictional-ml-instance demo
python -B workbench.py --workspace ../fictional-ml-instance serve
```

Open the printed loopback URL. The demo generates 240 invented rows with dimensionless features and ordinal days. It retains 118 training rows, 48 validation rows and 48 test rows; 26 rows are excluded by gaps, delayed labels or pending outcomes. It prepares two immutable experiments, records their evaluations, reviews one artifact, creates an eight-file private export, compares identical holdout cohorts and verifies a database backup.

The generated baseline chooses threshold `0.4` using validation F1. Its fictional test AUC is approximately `0.883478` and Brier score `0.167048`. These numbers describe only the generated task and implementation; they are not results from an original deployment or real customer data.

## Browser workflow

For a blank instance, run `init` instead of `demo`, then `serve`.

1. **Import:** load the generated fictional dataset or paste an explicitly selected dataset JSON. Inspect its fields before importing. Existing dataset IDs are immutable; identical imports are idempotent.
2. **Prepare:** choose a dataset, explicitly load its pinned configuration template, edit the experiment ID, timing boundaries, optimizer and threshold grid, then prepare. Advanced JSON editing is available. Invalid or conflicting requests retain drafts. Changing parameters requires a new experiment ID.
3. **Inspect:** review row exclusions, train-only means/scales, coefficients, validation threshold curve and reliability observations. Preparation does not produce test predictions or test metrics.
4. **Evaluate:** explicitly record the later holdout evaluation using the frozen learner, preprocessing and validation-selected threshold. This creates one immutable evaluation per experiment and resets current-artifact review to pending. It is not holdout secrecy or access control.
5. **Review/export:** record quality, privacy, rights and context assertions for the displayed artifact. Export requires evaluation and current-artifact approval. Inspect the private report and model before any separate sharing.
6. **Compare:** view test deltas only for experiments with evaluations of identical test cohorts. Reusing the holdout after seeing results makes it development data; a matching cohort does not establish independent final validation.

The UI includes keyboard-accessible forms, responsive SVG plots and literal text rendering of caller values. Panels are temporarily inert during a request to prevent response-driven loss of concurrent edits. Drafts are browser memory only and disappear on reload or shutdown. **Reload saved results** explicitly replaces displayed review fields; it does not change stored artifacts or configuration drafts.

## CLI

```sh
python -B workbench.py --workspace ../fictional-ml-instance datasets
python -B workbench.py --workspace ../fictional-ml-instance list
python -B workbench.py --workspace ../fictional-ml-instance show --experiment sample-baseline
python -B workbench.py --workspace ../fictional-ml-instance compare --left sample-baseline --right sample-comparison
python -B workbench.py --workspace ../fictional-ml-instance export --experiment sample-baseline
python -B workbench.py --workspace ../fictional-ml-instance backup
```

For a blank initialized instance, `import --file inbox/sample-dataset.json` imports the six-row example template. `example --dataset sample-ml` writes a fresh private experiment JSON and returns its relative file name with the actual dataset hash. Edit that selected file, then use `prepare --file` with its returned name. `evaluate --experiment` requires `--expected` equal to the prepared SHA-256 returned by preparation or `show`. `review --file` reads an explicit review request; see [contracts](docs/CONTRACT.md). Input files must be inside the selected workspace. Do not run another CLI command while its server owns the instance.

Stop through the UI or Ctrl+C. After an interrupted process, independently stop every process using that instance, then:

```sh
python -B workbench.py --workspace ../fictional-ml-instance recover --confirm-stopped
```

This removes only a verified empty session marker. It does not repair damage, replay work or automatically retrain/evaluate. Database backups include private datasets, parameters, evaluations and reviews, but omit inbox files and existing report directories. Retain the whole workspace separately when complete recovery is required. Schema checks do not establish hostile-database safety or production durability.

## Learning and evaluation boundaries

- One to eight finite numeric features; null values require null availability days. Mean imputation and population scaling use observed training values only. A wholly missing training feature is refused. Constant/tiny scales use one. No preprocessing is fitted on validation/test rows.
- Features must be declared available by each row's decision day. Train labels must be available strictly before validation start, and validation labels strictly before test start. Test labels must be available by the declared as-of day. Group IDs may not cross decision partitions, even if a row would later be purged. These are checks of supplied claims, not independent proof that feature history or group labels are truthful.
- Full-batch logistic regression minimizes mean binary cross-entropy plus half the L2 coefficient times squared feature-weight norm. The intercept is not regularized. A fixed iteration budget is not a convergence guarantee. No neural training, feature selection or automated tuning occurs.
- Thresholds maximize validation F1, then prefer nearest `0.5`, then lower threshold. A constant predictor uses training prevalence and independently selects its own validation threshold on the same grid.
- AUC uses average ranks for ties; average precision groups tied scores without interpolation. Undefined denominators remain null. Log loss clips scores to `[1e-15, 1-1e-15]`. Five reliability bins are descriptive. Scores are explicitly **not calibrated**.

Read the [design and formulas](docs/DESIGN.md), [exact contracts](docs/CONTRACT.md), [validation](docs/VALIDATION.md) and [source origins](docs/ORIGINS.md).

## Privacy, bounds and scope

Source contains fresh MIT code, invented templates and a deterministic fixture generator. No original operating implementation, customer records, private schema/configuration, paths, credentials, endpoints, logs, pretrained weights or third-party assets are included. Future trained model files are private outputs, not public source assets. JSON model files contain numbers and schema data, never pickle or executable payloads.

Maximum 1200 rows per dataset, eight features, 50 datasets, 100 experiments, 600 optimizer iterations, 19 thresholds, 5000 review records, 4 MiB per raw input/output file and 64 MiB store. Strict JSON rejects duplicate keys, nonfinite numbers and excessive nesting. Store-budget failure rolls back the transaction. New outputs never replace existing files; failed exports can retain partial directories with no manifest. No automatic purge occurs.

This is a trusted local single-operator application. Loopback, Host/Origin checks, session token, no-store, exact SQLite schema/version checks and public native Windows/POSIX I/O guards reduce accidental access; they are not multiuser authentication or protection from a hostile local process/filesystem. Supplied files/ancestors cannot be symlinks/reparse targets or multiply linked regular inputs within the documented helper boundary. Source/Git locations cannot hold private instances or output.

Dataset hashes, row/group IDs, outcome labels, model parameters, reviewer aliases/notes, predictions, reports and backups can be identifying. None are anonymized by this app. Approval is a local assertion, not permission to publish. No real-world model quality, medical/regulated suitability, live integration, remote hosting, mid-commit crash recovery or production backup/restore is established.

[MIT license](LICENSE), copyright TheOutlandsDev. [Collection index](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/systems).

## Tests and exact source archive

```sh
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../ml-experiment-workbench-source.zip
```

For actual browser acceptance, create and activate a separate development venv, then:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Ubuntu may require system dependencies via `python -m playwright install --with-deps chromium`. Windows CI also supplies the paired browser dependencies. Installation uses network access; runtime/demo need no external service. Browser tests start their own fresh loopback instance and refuse external requests. CI requires applicable native links on Windows/Ubuntu Python 3.12/3.13. Skipped local link fixtures are not passed checks. The source manifest pins the exact selected text files; no private instances, learned weights, reports, screenshots or dependency/browser binaries enter the focused ZIP.
