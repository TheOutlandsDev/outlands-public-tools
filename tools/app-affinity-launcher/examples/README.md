# Disposable example

`fixture_child.py` is original test-oriented source. It writes a new JSON file
containing its own PID, starting affinity, priority, working directory and
arguments. It is not a game and makes no network connection. Its output can
contain private local paths; keep generated files outside the public checkout.

Create a disposable private directory yourself. Find your actual Python
executable, for example with `python -c "import sys; print(sys.executable)"`.
Replace every fictional path below. Use an allowed logical processor selection
reported by a successful plan; processor 0 is only an example.

```text
python -m app_affinity plan --exe "D:\Python312\python.exe" --cores 0 --allow-existing --no-window -- "D:\Source\outlands-public-tools\tools\app-affinity-launcher\examples\fixture_child.py" --receipt "D:\Private\AffinityDemo\first.json" --label "two words"
python -m app_affinity launch --exe "D:\Python312\python.exe" --cores 0 --allow-existing --no-window --wait 10 -- "D:\Source\outlands-public-tools\tools\app-affinity-launcher\examples\fixture_child.py" --receipt "D:\Private\AffinityDemo\first.json" --label "two words"
```

`--allow-existing` is intentional: the Python executable is already in use by
the launcher itself. `--no-window` suppresses a new console for this fixture;
it does not hide a GUI application. `--wait` observes the child for up to ten
seconds. Its receipt file is created exclusively; rerun with a **new filename**.
The selected parent directory must already exist.

Inspect the private child JSON and launch receipt. The child mask should match
the requested mask and priority should be normal (`0x20`). These observations
exercise this disposable child, not any other application's behavior. The
standard test suite provides more generated native and failure-path checks.
