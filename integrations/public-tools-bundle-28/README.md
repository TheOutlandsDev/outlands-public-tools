# Build the twenty-eight-tool install bundle

This ZIP preserves thirty-five published input wheels from seven reviewed cohorts:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change, test/evidence and reliability/incident checks. Selector v1.5.0 adds
individual, group and all-tool install choices. The [start guide](START-HERE.md)
and COMPONENTS.json provide purposes, use cases, APIs, examples and result limits.
Earlier immutable releases remain available; other tools stay in the
[readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-28/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-28/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-28/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-28-1.5.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks thirty-five wheels from seven public
releases. Build refuses missing, extra or changed inputs. The deterministic ZIP has
forty fixed-metadata members including thirty-six wheels. Verification checks exact
inventory, manifests, wheel RECORD hashes and metadata, then exercises fifteen fresh
offline install choices: one individual from each group, every group and all tools.
Hosted Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum bytes.
Anonymous public-download installs repeat after publication. No application adapter,
live collector, incident update or operational recovery is included.
