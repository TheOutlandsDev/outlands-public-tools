# Setup and private exercise workflow

Verify the source ZIP using SHA256SUMS.txt, then extract into a new source folder.
Obtain an approved Python 3.12 or 3.15 installation separately. The release qualifies
3.12.16 and 3.15.2 on Windows/Ubuntu. No third-party dependency installation is needed.

## Windows

From the extracted source directory in ordinary PowerShell:

```powershell
py -3.15 -m venv --without-pip .venv
.\.venv\Scripts\python.exe kit.py inspect
.\.venv\Scripts\python.exe run_checks.py --report ..\seed-check.json
.\.venv\Scripts\python.exe kit.py evaluate --mode starter --task eval_003_typed_validation
.\.venv\Scripts\python.exe kit.py evaluate --mode reference --task eval_003_typed_validation
.\.venv\Scripts\python.exe kit.py prepare --task eval_001_pathlib_json_loader --out ..\my-json-exercise
```

Use py -3.12 or the actual approved executable for the other version. Activation,
execution-policy changes and admin access are unnecessary for these project venv
commands when Python is available and permitted by device policy.

## Ubuntu

Use Python with working venv support. If unavailable, obtain an approved install;
this guide does not change system packages, services or permissions.

```sh
python3.15 -m venv --without-pip .venv
.venv/bin/python kit.py inspect
.venv/bin/python run_checks.py --report ../seed-check.json
.venv/bin/python kit.py evaluate --mode starter --task eval_003_typed_validation
.venv/bin/python kit.py evaluate --mode reference --task eval_003_typed_validation
.venv/bin/python kit.py prepare --task eval_001_pathlib_json_loader --out ../my-json-exercise
```

The starter typed-validation report intentionally records an ImportError because
the unchanged starter does not define UserRecord. The separate reference runs all
five original tests and passes. The same separation applies to the CSV result class.
Starter reports distinguish declared tests, actual methods and failed-load entries.
The full report records each outcome and test ID rather than converting expected
starter defects into passing assertions. All positive release checks must pass.

## Work on a prepared copy

Open the new my-json-exercise folder, read task.md and edit starter/json_loader.py.
Keep tests unchanged if you want to compare against the original exercise. From
that new folder, use your selected Python executable:

```text
python -m unittest discover -s tests
```

The initial copied starter is deliberately flawed, so this ordinary test command
fails until it is repaired. It is your own code execution outside the kit's reviewed
fixture runner; the runner's audit policy is not inherited. Review code before
running it. Reference repairs under references/ are separate teaching answers and
are not copied by prepare. They are useful for checking the tests, not proof that
an agent solved an unseen task. Keep reference answers out of an evaluation prompt
when you want an unaided exercise. No training, retrieval or model call happens here.

Use fresh output/report names. Existing destinations and package-internal outputs
are refused. Inputs/instructions in the original/ tree remain byte-pinned. Keep
your exercises, reports and generated caches private and outside Git.

## Original helpers

The preserved original/scripts/check_pack_integrity.py checks required paths and
source-record keys; it is not a cryptographic source verifier. The original example
runner is qualified unchanged. catalog_to_markdown.py overwrites its original index
path, so release checks run it only in a disposable copy. The original evaluation
template accepts a path and runs unittest without the new fixture audit hooks.
Release checks exercise that template only on a known separate reference in a
disposable copy. Prefer the fixed-task CLI for checking the shipped fixtures.

## Reproduce release qualification

packaging/build.py creates an exact deterministic text-source ZIP from committed
allowlisted files in a new external output directory. packaging/prepare_python.py
extracts one complete hash-pinned SDK from PYTHON-LOCK.json into a new prefix; no
global installation occurs. Each CI host independently rebuilds matching ZIP and
build-manifest bytes, extracts fresh source and creates a venv without pip. It
verifies there are zero installed dependency distributions, runs all positive and
starter populations, checks copied CLI/exercise preparation outside the source
directory, and confirms every manifested file is unchanged. Actual results are
published as VALIDATION.json; no interpreter or dependency binary is in this ZIP.
