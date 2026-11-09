# Install and use the annotation and geometry tools

These four independent MIT wheels review supplied annotation declarations without
opening image assets. Supply Python 3.12 or 3.13; runtime dependencies are the
standard library only. See the [terms and evidence limits](../../methodology/ANNOTATION-GEOMETRY.md)
and [component contracts](components.json).

| Tool | Selected question | Boundary |
| --- | --- | --- |
| [Annotation manifest checker](../../tools/annotation-manifest-checker/README.md) | Do image, taxonomy and annotation references agree? | Does not validate image bytes or polygon geometry. |
| [Polygon geometry checker](../../tools/polygon-geometry-checker/README.md) | Are supplied vertices a simple polygon within declared dimensions? | Does not inspect pixels or repair a ring. |
| [Bounding box converter](../../tools/bounding-box-converter/README.md) | Do declared box conventions convert exactly? | Does not clip, round or modify an asset. |
| [Annotation export handoff checker](../../tools/annotation-export-handoff-checker/README.md) | Do selected annotations, categories, approvals and expected counts agree? | Does not authenticate approval or export a dataset. |

Reports retain selected identifiers and hashes. Keep real inputs and reports private.
A PASS is consistency within the supplied records, not image correctness, label
truth, approval authenticity or compatibility with an external annotation format.

## Install

Download the selected wheels and SHA256SUMS.txt from the
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/annotation-geometry-wheels-v1.0.0).
Verify the hashes before installing. Create a fresh environment outside this
checkout with Python 3.12 or 3.13 and run:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_polygon_geometry_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-annotation-geometry-collection==1.0.0
```

The collection requires all five wheels in one directory and pins its four
components exactly. Run `outlands-annotation-geometry` to list commands.
Each component has `outlands-TOOL-demo` for an embedded fictional example and
`outlands-TOOL --input PRIVATE_JSON` for an explicit private input. CLI exit
codes are 0 PASS, 1 REVIEW_REQUIRED, 2 refusal and 130 interruption. The source
guides document bounded schemas, result meanings and guarded fresh output paths.

## Python API

Each package exposes `check(raw_json_bytes)`. For example:

```python
from importlib.resources import files
from outlands_polygon_geometry_checker.polygons import check

raw = files("outlands_polygon_geometry_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["valid_polygons"] == 1
assert report["artifact_bytes_verified"] is False
```

Run `python -B integrations/annotation-geometry/exercise.py` in an environment
with the collection installed. The exercise uses only embedded fictional
examples. It checks four positive cases, four review cases, shared manifest and
handoff pins, a simple polygon, an exact box conversion and a bounded handoff.

The polygon and box examples share a declared image and coordinates with the
manifest example; the handoff uses the same taxonomy, image and annotation
declarations. These are supplied metadata relationships. No image is decoded,
read, hashed or checked against those declarations.

## Package verification

`build_wheels.py` reads only SOURCE-MANIFEST-pinned public source and fictional
examples. `verify_wheels.py` checks wheel members, RECORD hashes, fixed ZIP
metadata, exact release hashes, fresh individual installs, the collection,
commands, APIs and positive/review examples. `compare.py` checks byte-identical
platform builds. `public_download.py` anonymously verifies public assets and
repeats fresh installs. Build output must be an existing empty directory outside
the repository.
