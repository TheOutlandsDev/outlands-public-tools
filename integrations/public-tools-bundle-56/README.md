# Build the fifty-six-tool install bundle

This ZIP preserves seventy public input wheels from fourteen reviewed groups:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change, test/evidence, reliability/incident, metrics/traces,
document/evidence, relational review, ingestion control, worker/queue review,
configuration review and API request/response review. Selector v1.12.0 supports
individual, group and all-tool installs. The [start guide](START-HERE.md) and COMPONENTS.json give purposes, use
cases, APIs, examples and result limits. Earlier immutable releases remain
available; other tools remain in the [readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-56/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-56/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-56/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-56-1.12.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks seventy wheels from fourteen public
releases. Build refuses missing, extra or changed inputs. The deterministic ZIP
has seventy-five fixed-metadata members including seventy-one wheels. Verification checks
inventory, manifests and wheel RECORD hashes/metadata, then exercises twenty-nine
fresh offline install choices: one individual from each group, every group and all
tools. Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum bytes.
Anonymous public-download installs repeat after release. No application adapter,
database connection, worker/broker access, actual setting validation, configuration
change, migration execution or live API behavior verification is included.
