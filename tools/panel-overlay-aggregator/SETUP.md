# Setup and fictional walkthrough

Verify the downloaded ZIP using SHA256SUMS.txt before extracting into a new source
folder. Obtain Python and dependencies separately. Use an ordinary user-owned venv
when approved Python is available; activation/admin or execution-policy changes
are unnecessary for these project commands.

## Windows

From the extracted source directory in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.\.venv\Scripts\python.exe run_checks.py
.\.venv\Scripts\python.exe synthetic.py --out ..\invented-panel-inputs
.\.venv\Scripts\python.exe guarded_aggregate.py --root ..\invented-panel-inputs --manifest sites_manifest.csv --out ..\invented-panel-result.csv
```

Use py -3.15 or the actual approved Python executable for the other qualified minor.
Both builds need tkinter even though the guarded launcher opens no desktop window.

## Ubuntu

Use Python with venv, tkinter and the required native-library support. If these are
missing, obtain an approved installation; this guide changes no system packages.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.venv/bin/python run_checks.py
.venv/bin/python synthetic.py --out ../invented-panel-inputs
.venv/bin/python guarded_aggregate.py --root ../invented-panel-inputs --manifest sites_manifest.csv --out ../invented-panel-result.csv
```

The invented inputs contain three PNG crops, one manifest and one XML reference.
Two VX crops have +4/+8 pixel shifts at a forty-pixel pitch; their median is about
+1.5 um under the original pitch assumption. A portrait VY crop has -4 pixels,
about -1 um. XML references are +0.25/-0.5 um. Expected differences are about
+1.25/-0.5 um. EXPECTED.json records the synthetic tolerance. All result CSVs and
generated images are private outputs, not calibrated measurement records.

The JSON completion report contains counts and the CSV hash, not panel identifiers
or real file paths. Exit 0 means a finite complete table was computed; it remains
unapproved. Exit 2 means refusal/failure. A rerun using the same output name is
refused without changing its bytes. Use fresh fixture/output names.

## Preserved checks and original CLI

```text
python original/verify_panel_overlay_axisfix.py
python -X utf8 original/panel_overlay_aggregate_v2_axisfix.py --config YOUR_TRUSTED_CONFIG.toml
```

The public verification copy retains all nine original assertions and code
structure; only unclear fixture identifiers/numbers are replaced with invented
literals. The raw original is retained privately and passed unchanged. The
implementation itself is byte-preserved. BASELINE.json binds the public files.

The original config has a paths table with out_root, analyzer and panel_csv. It
recursively discovers the two supported manifest basenames, imports the specified
trusted Python analyzer, accepts paths using its original current-directory rules
and can overwrite panel_csv. It may write its CSV before a completion-print error
under a legacy Windows encoding; UTF-8 mode avoids that preserved print limitation.
The guarded launcher is the recommended entry point and does not use that config.
Do not apply its safeguards to the legacy command by assumption.

## Reproduce qualification

The committed packaging/build.py creates a deterministic text-source ZIP and build
manifest in a new external directory. packaging/prepare_python.py extracts exactly
one hash-pinned complete SDK from PYTHON-LOCK.json into a new prefix, without global
installation. Each native CI job independently rebuilds matching package bytes,
installs hash-locked binary wheels into a new venv, checks exact versions/pip
consistency, executes 24 tests from the extraction and invokes the copied guarded
CLI from another directory. Actual records are published as VALIDATION.json.
