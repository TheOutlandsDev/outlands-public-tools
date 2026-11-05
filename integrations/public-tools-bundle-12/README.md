# Build the twelve-tool install bundle

This bundle combines **only** the twelve independently qualified Python tools
from the Model Routing, AI Decision Contracts and Probability Integrity wheel releases. It preserves
their fifteen exact released wheel bytes and adds one selector wheel. Extract the
ZIP to install one tool, one four-tool group, or all twelve. The
[included start guide](START-HERE.md) and generated `COMPONENTS.json` describe
each choice, use case, entry point, input/result format and limit.

The [release plan](release.json) pins the two public output assets. The source
ZIPs and Toolkit 0.9.0 remain separate. The other public tools in the
[install-readiness plan](../INSTALL-PLAN.md) are outside this bundle.

## Rebuild from the exact public wheels

Supply Python 3.12 or 3.13, setuptools 80.9.0 and wheel 0.45.1. Create two
empty directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-12/fetch_inputs.py --output EMPTY_INPUT_DIRECTORY
python -B integrations/public-tools-bundle-12/build.py --inputs EMPTY_INPUT_DIRECTORY --output EMPTY_OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-12/verify.py --archive EMPTY_OUTPUT_DIRECTORY/outlands-public-tools-12-1.1.0.zip --checksums EMPTY_OUTPUT_DIRECTORY/SHA256SUMS.txt
```

`fetch_inputs.py` anonymously downloads fifteen exact wheel assets from the three
published releases. `build.py` refuses missing, extra or changed inputs, then
creates the selector wheel and fixed-metadata ZIP. `verify.py` checks all 20
archive members and wheel metadata, then fresh-installs seven choices offline:
one tool from each group, each four-tool group, and all twelve. The hosted
workflow compares exact ZIP/checksum bytes across Windows and Ubuntu with
Python 3.12/3.13. Its manual public-download run exercises the published ZIP
after release.

The selector declares dependencies; it does not run a cross-tool workflow or
integrate with any OUTLANDS system. Actual input/report data stays private.
