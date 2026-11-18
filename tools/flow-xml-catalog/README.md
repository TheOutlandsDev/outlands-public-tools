# Offline Flow XML Catalog and Comparator

Verify a manifest of saved flow XML files against their SHA-256 and declared
metadata. Compare two revisions by step position, keep repeated steps and
reference rework paths, and produce a normalized XML reference export.

Both original runtime modules are preserved byte for byte. The public suite has
all 19 original cases with fictional flow names, identifiers and hashes. The
source edition uses five fictional XML fixtures. It runs locally with Pydantic.

See the [usage guide](SETUP.md) and [source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/flow-xml-catalog-v0.1.0).
