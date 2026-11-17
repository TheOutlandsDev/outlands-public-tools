# PNG Vernier Group Offset Analyzer Rev 3b

Analyze the displacement between two bar groups in a selected PNG using the
original Rev 3b profile sampling, extrema detection, robust fitting and aggregation.
The four selected original files are preserved byte for byte under `original/`:
two identical revision-named implementations, their verification script and patch
notes. `vernier.py` is a separate adapter, not a rewritten measurement engine.

Download the [source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/vernier-analyzer-v0.1.0).
See [setup and synthetic walkthrough](SETUP.md), [qualification](docs/QUALIFICATION.md)
and [source origins](docs/ORIGINS.md). Source only: no interpreter, dependency wheel,
original microscope image, XML, customer data, calibration record or raw log.

```text
python vernier.py YOUR_PRIVATE_IMAGE.png
python vernier.py YOUR_PRIVATE_IMAGE.png --plots NEW_PRIVATE_PLOT_DIRECTORY
```

The CLI accepts a file path without opening a picker and emits JSON on stdout.
Exit 0 means a finite result was computed; it does not mean quality approval.
Exit 2 is a refused/failed input or analysis. `--help` needs no third-party imports.
The adapter uses the original array loader, orientation, sampling/QC and alignment
functions. PNGs are limited to 16 MiB and 4 million pixels; animations, symlink/
reparse paths, absent sampling groups, wholly featureless groups and nonfinite
results are refused. Parent directories must be stable and trusted: these path
checks are not an OS security boundary against concurrent malicious replacement.

The preserved gate falls back to ranked lines when fewer than eight pass QC.
Fallback can retain failed lines. JSON always says `quality_approved=false`, lists
fallback use and reports `RESULT_REQUIRES_REVIEW`. Do not treat fallback as passing
the original quality gate. The wrapper additionally refuses groups with no retained
line having sufficient contrast and band count. This is an adapter policy; the
original fallback code and file-picker behavior remain unchanged.

One vernier assumes a 10 micrometre center-to-center pitch. The original pixel
conversion uses `INTERP_LEN / axis_length` although interpolation includes both
endpoints; its small length-versus-length-minus-one bias is retained and tested.
The reported spread/standard error is not a calibrated uncertainty budget. Generated
test images establish numerical behavior only, not accuracy on real microscopes,
distorted/noisy specimens, production acceptance or all possible failure modes.

Plot output uses a new directory and never replaces existing files. A failed write
may leave a partial directory; inspect it before removal. Inputs and plots can be
private; store them outside Git. Matplotlib may create a font/config cache; select
a private `MPLCONFIGDIR` if required. Native use needs NumPy, Pillow, Matplotlib and
a Python build with tkinter. Qualification uses hash-locked packages and pinned
Python 3.12.16/3.15.2 on Windows x64 and Ubuntu x86-64. Interactive desktop picking
and display are separate from the tested Agg plot rendering.
