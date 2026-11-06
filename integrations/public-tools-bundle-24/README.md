# Build the twenty-four-tool install bundle

This ZIP preserves thirty reviewed published wheel inputs from six cohorts:
model routing, AI decision contracts, probability integrity, cache/retry,
review/change and test/evidence. Selector v1.4.0 adds one-tool, group and all-tool
installation choices. The [start guide](START-HERE.md) and COMPONENTS.json provide
human and AI entry points with explicit APIs, examples, result meanings and limits.
Earlier immutable releases remain available. Other tools stay in the
[readiness plan](../INSTALL-PLAN.md).

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-24/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-24/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-24/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-24-1.4.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

Fetch anonymously downloads thirty pinned wheels from six public releases. Build
refuses missing, extra or changed inputs. The archive has thirty-five fixed-metadata
members including thirty-one wheels. Verification checks exact inventory, manifests,
wheel RECORD hashes and metadata, then tests thirteen fresh offline install choices:
one individual from each group, each group, and all twenty-four. Hosted Windows/Ubuntu
Python 3.12/3.13 builds compare exact ZIP and checksum bytes. A public-download matrix
repeats fresh installs after publication. No application adapter is included.
