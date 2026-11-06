# Build the fifty-two-tool install bundle

This ZIP preserves sixty-five public input wheels from thirteen reviewed groups:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change, test/evidence, reliability/incident, metrics/traces,
document/evidence, relational review, ingestion control, worker/queue review and
configuration review. Selector v1.11.0 supports individual, group and all-tool
installs. The [start guide](START-HERE.md) and COMPONENTS.json give purposes, use
cases, APIs, examples and result limits. Earlier immutable releases remain
available; other tools remain in the [readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-52/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-52/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-52/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-52-1.11.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks sixty-five wheels from thirteen public
releases. Build refuses missing, extra or changed inputs. The deterministic ZIP
has seventy fixed-metadata members including sixty-six wheels. Verification checks
inventory, manifests and wheel RECORD hashes/metadata, then exercises twenty-seven
fresh offline install choices: one individual from each group, every group and all
tools. Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum bytes.
Anonymous public-download installs repeat after release. No application adapter,
database connection, worker/broker access, actual setting validation, configuration
change or migration execution is included.
