# Build the sixty-eight-tool install bundle

This ZIP preserves eighty-five public input wheels from seventeen reviewed
groups, adding [maintenance and service](../maintenance-service/README.md) to the
earlier sixty-four-tool collection. Selector v1.15.0 supports individual, group
and all-tool installs. The [start guide](START-HERE.md) and COMPONENTS.json
describe purposes, use cases, APIs, examples and limits. Earlier immutable
releases remain available; other tools remain in the
[readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty
absolute input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-68/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-68/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-68/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-68-1.15.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks eighty-five wheels from seventeen
public releases. Build refuses missing, extra or changed inputs. The
deterministic ZIP has ninety fixed-metadata members, including eighty-six
wheels. Verification checks the inventory, manifests and wheel RECORD hashes,
then exercises thirty-five fresh offline install choices: one individual from
each group, every group and all tools. Windows/Ubuntu Python 3.12/3.13 builds
compare exact ZIP/checksum bytes. Anonymous public-download installs repeat
after release. No application adapter, browser automation or live system
behavior verification is included.
