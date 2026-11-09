# Build the sixty-tool install bundle

This ZIP preserves seventy-five public input wheels from fifteen reviewed
groups, adding [forms and interaction](../forms-interaction/README.md) to the
earlier fifty-six-tool collection. Selector v1.13.0 supports individual, group
and all-tool installs. The [start guide](START-HERE.md) and COMPONENTS.json
describe purposes, use cases, APIs, examples and limits. Earlier immutable
releases remain available; other tools remain in the
[readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty
absolute input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-60/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-60/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-60/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-60-1.13.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads and hash-checks seventy-five wheels from fifteen
public releases. Build refuses missing, extra or changed inputs. The
deterministic ZIP has eighty fixed-metadata members, including seventy-six
wheels. Verification checks the inventory, manifests and wheel RECORD hashes,
then exercises thirty-one fresh offline install choices: one individual from
each group, every group and all tools. Windows/Ubuntu Python 3.12/3.13 builds
compare exact ZIP/checksum bytes. Anonymous public-download installs repeat
after release. No application adapter, browser automation or live system
behavior verification is included.
