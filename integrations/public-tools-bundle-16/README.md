# Build the sixteen-tool install bundle

This versioned ZIP combines the reviewed Model Routing, AI Decision Contracts,
Probability Integrity and Cache/Retry wheel releases. It preserves twenty exact
published wheel inputs and adds selector v1.2.0: sixteen independent tools, four
four-tool collections and one selector. The [start guide](START-HERE.md) and
`COMPONENTS.json` describe purposes, use cases, APIs, formats and limits.

The [release plan](release.json) pins the ZIP and outer checksum. Older eight- and
twelve-tool builds keep their own source and releases. Other public tools remain
in the [readiness plan](../INSTALL-PLAN.md) and outside this ZIP.

## Rebuild and qualify

Supply Python 3.12 or 3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty
absolute input/output directories outside the repository, then run:

```text
python -B integrations/public-tools-bundle-16/fetch_inputs.py --output INPUT_DIRECTORY
python -B integrations/public-tools-bundle-16/build.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY
python -B integrations/public-tools-bundle-16/verify.py --archive OUTPUT_DIRECTORY/outlands-public-tools-16-1.2.0.zip --checksums OUTPUT_DIRECTORY/SHA256SUMS.txt
```

The fetch step downloads twenty wheels anonymously from four public releases and
checks their exact hashes. The builder refuses changed, missing or extra inputs.
The fixed-metadata ZIP has twenty-five members, including twenty-one wheels.
Verification checks exact inventory, manifest hashes, wheel RECORD data and nine
fresh offline install choices: one individual from each group, each full group,
and all sixteen. Hosted Windows/Ubuntu Python 3.12/3.13 builds compare exact ZIP
and checksum bytes. A manual public-download matrix repeats installs after release.

The selector installs declared packages and lists actual installed state. It does
not orchestrate tools or connect them to an application. Keep real inputs private.
