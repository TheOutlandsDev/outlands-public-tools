# Offline RDL Dataset Catalog Builder

Inventory datasets, parameters, fields, data-source references and report logic
from local SSRS Report Definition Language files. The builder saves each parsed
dataset command as text and records its SHA-256. The review queue highlights
dependencies for human review. SQL and report expressions are handled as text.

The source edition retains the original extraction and classification logic and
all ten tests. It uses fictional reports, neutral database and source labels,
and an `examples/` default input folder. Python's standard library provides the
runtime, qualified on Windows and Ubuntu with Python 3.12.16 and 3.15.2.

See the [usage guide](SETUP.md) and the [source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/rdl-dataset-catalog-v0.1.0).
