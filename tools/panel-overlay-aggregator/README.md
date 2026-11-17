# Panel Overlay Aggregator - axis-fix revision

Combine explicitly selected image-crop manifests with axis-specific XML reference
values and write panel CSV comparisons using the original axis-fix implementation.
The original core is preserved byte for byte. A separate guarded launcher invokes
its aggregation, fixed-sampling analysis, median, reference-fallback and difference
routines. The previously published Rev 3b numerical engine is included with its
exact source pin; no object detector, model, original image or operational XML is
bundled. The word YOLO in the legacy columns refers to existing manifest labels,
not included inference or detection.

Download the [standalone source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/panel-overlay-aggregator-v0.1.0).
Read [setup](SETUP.md), [source origins](docs/ORIGINS.md) and
[qualification](docs/QUALIFICATION.md) before using private data.

```text
python guarded_aggregate.py --root PRIVATE_INPUT_DIRECTORY --manifest sites_manifest.csv --out NEW_PRIVATE_OUTPUT.csv
```

Paths inside CSV rows are relative to the selected input root, or absolute ordinary
paths within it. They are not relative to each manifest's folder. The output parent
must already exist and the new output file must be outside the input root. The
launcher accepts repeated --manifest arguments; it does not recursively discover
files or import an arbitrary analyzer specified by a config file. Original legacy
commands remain available for trusted use with their original limitations.

Input limits: eight explicit manifests, 256 rows in total, 1 MiB per manifest,
512 KiB per XML, 16 MiB/four million pixels per single-frame PNG, 64 MiB selected
file bytes and 16 million processed pixels in total. XML must be UTF-8 without
DOCTYPE/entities; depth is limited to 16 and nodes to 2,048. Selected reference
keys must be unique, finite and have empty/OK status. Unknown/non-overlay reference
measurements remain outside the supported subset. Optional absent references yield
blank comparison cells; an explicitly named missing file is refused.

Alias conflicts, unsupported measurement rows, conflicting reference files for the
same panel, nonfinite/incomplete analysis, featureless groups, linked/reparse paths,
path escapes, input changes and an existing output are refused. The source/analyzer
pins are checked before import. New output uses exclusive creation. A failed disk
write may leave a partial new file; existing files are never replaced by the guarded
launcher. Use stable trusted parents and inputs: validation followed by legacy reads
is not a security barrier against concurrent malicious filesystem changes.

Every computed result is marked RESULT_REQUIRES_REVIEW, quality_approved=false and
calibration_verified=false. Manifest labels vernier_h/vernier_v select VX/VY axes;
sampling does not follow the image aspect ratio. This aggregator directly calls
fixed sampling in the engine and DOES NOT apply Rev 3b's expanded sampling/QC gate.
A separate featureless-input refusal does not turn it into that gated algorithm.
Legacy corner-only XML fallback is retained and counted in the JSON result.

The original assumed 10 micrometre bar pitch, pixel-length conversion bias and
spread-based sigma are retained. A median of supplied sigma estimates is not a
calibrated uncertainty for the median. Synthetic tests do not establish instrument
accuracy, production acceptance or real-specimen performance. The original check
script's nine assertions are retained with invented fixture literals; the raw
original remains unchanged privately. See origins for that explicit distinction.

Requirements: Python 3.12.16 or 3.15.2 with tkinter, NumPy, Pillow and Matplotlib.
The source package contains no interpreter, third-party wheel, original dataset,
configuration, credential or raw log. Keep private inputs, outputs and caches out
of Git. The public catalog registers this source independently of older immutable
toolkit/wheel bundles.
