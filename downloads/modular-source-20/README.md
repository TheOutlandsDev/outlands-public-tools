# Modular Source Tools 20

This is a separately qualified source-only bundle of the 20 MIT tools published in Batches 94–98. It does not replace the active frozen Toolkit 0.9.0 download or include the other tools and systems listed in the repository catalog.

The [exact selection](plan.json) pins public source commit `82ff97aed508700ffb129370351580b5586fd532`. The builder takes only the 266 selected Git blob files. Its output is a ZIP containing those files, a neutral README, and a member hash manifest, plus a separate `SHA256SUMS.txt`. ZIP timestamps and permissions are fixed synthetic values. The archive contains no `.git` history, runtime, personal profile, private instance, local configuration, or private source. The MIT license files retain the public TheOutlandsDev attribution.

## Build and check

From a complete Git checkout with Python 3.12/3.13, choose a new external output directory that already exists:

```text
python -B downloads/modular-source-20/build.py --output NEW_EXTERNAL_DIRECTORY
python -B downloads/modular-source-20/verify.py --archive NEW_EXTERNAL_DIRECTORY/outlands-modular-tools-20-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
python -B downloads/modular-source-20/accept.py --archive NEW_EXTERNAL_DIRECTORY/outlands-modular-tools-20-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
```

The pinned ZIP SHA-256 is `2380a9bfee428a35526aa896d753e946c159b2adef87ff50f59581c80124d215`. Verification checks every member path, byte hash and archive metadata. Fresh extraction runs 20 source-manifest checks and 20 invented CLI examples. Hosted Windows/Ubuntu builds on Python 3.12/3.13 must match byte for byte. Keep real inputs and reports private; structural summaries can reveal names and counts. This qualification does not establish production suitability or clear any original private application family.

After publication, the workflow's manual dispatch runs `public_download.py` on Windows and Ubuntu against the actual public release assets. The release is complete only after both public-download jobs pass.

See [release review](REVIEW.md) and [release notes](RELEASE.md).
