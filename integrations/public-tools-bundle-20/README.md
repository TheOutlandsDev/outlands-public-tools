# Build the twenty-tool install bundle

This ZIP combines the reviewed Model Routing, AI Decision Contracts, Probability
Integrity, Cache/Retry and Review/Change wheel releases. It preserves twenty-five
published wheel inputs and adds selector v1.3.0: twenty independent tools, five
group installers and one selector. The [start guide](START-HERE.md) and generated
COMPONENTS.json give each tool's purpose, use case, API, formats and limits.

The [release plan](release.json) pins the ZIP and outer checksum. Earlier bundle
versions keep their own source and releases. Other tools remain in the
[readiness plan](../INSTALL-PLAN.md) and outside this ZIP.

## Rebuild and qualify

Supply Python 3.12 or 3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty
absolute input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-20/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-20/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-20/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-20-1.3.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch downloads twenty-five wheels anonymously from five public releases and
checks exact hashes. Build refuses changed, missing or extra inputs. The ZIP has
thirty fixed-metadata members, including twenty-six wheels. Verification checks
inventory, manifests and wheel RECORD data, then tests eleven fresh offline choices:
one individual from each group, each complete group, and all twenty. Hosted
Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP/checksum bytes. A manual
public-download matrix repeats installs after publication.

The selector installs packages and lists actual installed state; it does not
orchestrate tools or install application adapters. Actual project inputs stay private.
