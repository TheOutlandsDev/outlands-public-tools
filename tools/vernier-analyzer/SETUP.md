# Setup and synthetic-image walkthrough

Verify `SHA256SUMS.txt` against the downloaded ZIP before extracting it into a new
source directory. Read README.md for the retained QC fallback and calibration
limits. Obtain Python and dependencies separately; this ZIP contains text source.

## Windows

Use an ordinary PowerShell terminal, Python 3.12 or 3.15 with tkinter, and a new
project venv. No activation or execution-policy change is needed. From extraction:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.\.venv\Scripts\python.exe run_checks.py
.\.venv\Scripts\python.exe synthetic.py --out ..\invented-bars
.\.venv\Scripts\python.exe vernier.py ..\invented-bars\positive.png
.\.venv\Scripts\python.exe vernier.py ..\invented-bars\portrait.png --plots ..\invented-plots
```

Use `py -3.15` or the actual approved Python executable for the other qualified
minor. User-owned venvs do not themselves require admin. Follow device policy.

## Ubuntu

Use Python 3.12 or 3.15 with venv, tkinter and working native-library support.
If these are missing, obtain an approved Python installation; this guide does not
change system packages, permissions or services. From extraction:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.venv/bin/python run_checks.py
.venv/bin/python synthetic.py --out ../invented-bars
.venv/bin/python vernier.py ../invented-bars/positive.png
.venv/bin/python vernier.py ../invented-bars/portrait.png --plots ../invented-plots
```

The invented positive and portrait cases have a four-pixel shift on a forty-pixel
bar pitch: approximately +0.1 verniers, or +1 micrometre under the original assumed
10 micrometre pitch. `zero.png` gives zero; `negative.png` gives approximately
-0.1 verniers; `blank.png` is refused with exit 2/INSUFFICIENT_PATTERN. See generated
EXPECTED.json for the fixed synthetic tolerances. All successful JSON still needs
human review. Plots are six PNGs rendered with Agg; creating them does not open a
desktop window. Use fresh names for generator/plot folders; reruns refuse overwrite.

## Preserved command and checks

```text
python original/verify_patch.py
python original/Vern_Analyze_v2.py --no-display
```

The existing verification script compiles source, invokes help and prints feature
markers. It does not assert all outcomes or test numerical correctness. The separate
release tests assert its four expected outputs and zero help exit. The original
command still uses a Tk file picker even with --no-display; that flag only disables
plots. It needs a desktop and is not the headless CLI. The alias Vern_Analyze_v3b.py
has exactly the same bytes. Source pins in BASELINE.json retain all four originals.

## Reproduce package qualification

The packaging helper downloads only the explicit hash-pinned standalone CPython
archive listed in PYTHON-LOCK.json into a NEW directory; it does not install globally.
From the source checkout, create a committed source package using packaging/build.py
with --out NEW_ABSOLUTE_EXTERNAL_DIRECTORY. CI independently rebuilds that package
on each host, compares exact ZIP/manifest bytes, installs locked wheels into a fresh
venv, verifies distributions/pip consistency, runs all 17 tests from the extraction
and invokes the copied CLI from a different directory. See docs/QUALIFICATION.md.
