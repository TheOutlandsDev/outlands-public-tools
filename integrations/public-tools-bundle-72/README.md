# Build the seventy-two-tool install bundle

This ZIP preserves ninety public input wheels from eighteen reviewed
groups, adding [stock and fulfillment](../stock-fulfillment/README.md) to the
earlier sixty-eight-tool collection. Selector v1.16.0 supports individual, group
and all-tool installs. The [start guide](START-HERE.md) and COMPONENTS.json
describe purposes, use cases, APIs, examples and limits. Earlier immutable
releases remain available; other tools remain in the
[readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty
absolute input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-72/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-72/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-72/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-72-1.16.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks ninety wheels from eighteen
public releases. Build refuses missing, extra or changed inputs. The
deterministic ZIP has ninety-five fixed-metadata members, including ninety-one
wheels. Verification checks the inventory, manifests and wheel RECORD hashes,
then exercises thirty-seven fresh offline install choices: one individual from
each group, every group and all tools. Windows/Ubuntu Python 3.12/3.13 builds
compare exact ZIP/checksum bytes. Anonymous public-download installs repeat
after release. No application adapter, browser automation or live system
behavior verification is included.
