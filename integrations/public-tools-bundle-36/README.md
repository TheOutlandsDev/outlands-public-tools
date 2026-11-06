# Build the thirty-six-tool install bundle

This ZIP preserves forty-five public input wheels from nine reviewed groups:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change, test/evidence, reliability/incident, metrics/traces and document/evidence.
Selector v1.7.0 supports individual, group and all-tool installs. The
[start guide](START-HERE.md) and COMPONENTS.json give purposes, use cases, APIs,
examples and result limits. Earlier immutable releases remain available; other
tools remain in the [readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-36/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-36/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-36/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-36-1.7.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks forty-five wheels from nine public
releases. Build refuses missing, extra or changed inputs. The deterministic ZIP
has fifty fixed-metadata members including forty-six wheels. Verification checks
inventory, manifests and wheel RECORD hashes/metadata, then exercises nineteen
fresh offline install choices: one individual from each group, every group and
all tools. Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum bytes.
Anonymous public-download installs repeat after release. No application adapter,
live collector, model call, corpus search or factual-truth review is included.
