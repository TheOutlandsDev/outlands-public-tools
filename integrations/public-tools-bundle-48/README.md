# Build the forty-eight-tool install bundle

This ZIP preserves sixty public input wheels from twelve reviewed groups:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change, test/evidence, reliability/incident, metrics/traces,
document/evidence, relational review, ingestion control and worker/queue review.
Selector v1.10.0 supports individual, group and all-tool installs. The
[start guide](START-HERE.md) and COMPONENTS.json give purposes, use cases, APIs,
examples and result limits. Earlier immutable releases remain available; other
tools remain in the [readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-48/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-48/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-48/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-48-1.10.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks sixty wheels from twelve public
releases. Build refuses missing, extra or changed inputs. The deterministic ZIP
has sixty-five fixed-metadata members including sixty-one wheels. Verification
checks inventory, manifests and wheel RECORD hashes/metadata, then exercises
twenty-five fresh offline install choices: one individual from each group, every
group and all tools. Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum
bytes. Anonymous public-download installs repeat after release. No application
adapter, database connection, worker/broker access, job execution, acknowledgement
or result commit is included.
