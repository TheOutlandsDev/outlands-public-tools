# Grouped Reports 4 source bundle

This source-only bundle contains four already public MIT tools: unit catalog contract checking, conversion path checking, quantity reconciliation, and revision scenario comparison. It is separate from Toolkit 0.9.0, Modular Source Tools 20, and Grouped Reports 4.

The [exact selection](plan.json) pins public source commit `807328001893d82bb3daaa6349c4ebb787b91a76`. The builder takes only 68 selected Git blob files. Its ZIP adds a neutral README and member hash manifest; `SHA256SUMS.txt` is separate. ZIP timestamps and permissions are fixed synthetic values. No Git history, runtime, user profile, private instance, local configuration, or private source is included. MIT licenses retain public TheOutlandsDev attribution.

## Build and check

From a complete Git checkout with Python 3.12/3.13, choose a new external output directory that already exists:

```text
python -B downloads/unit-conversion-4/build.py --output NEW_EXTERNAL_DIRECTORY
python -B downloads/unit-conversion-4/verify.py --archive NEW_EXTERNAL_DIRECTORY/outlands-unit-conversion-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
python -B downloads/unit-conversion-4/accept.py --archive NEW_EXTERNAL_DIRECTORY/outlands-unit-conversion-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
```

The pinned ZIP SHA-256 is `f2ac88771def48f915d7bac9130f95d4fced7012f568748ea8844d2d926ddca3`. Verification checks every member path, byte hash and archive metadata. Fresh extraction runs four source-manifest checks and four fictional CLI examples. The revision comparison example intentionally returns `REVIEW_REQUIRED` because conversion outcomes change. Hosted Windows/Ubuntu builds on Python 3.12/3.13 must match byte for byte. Reports can contain supplied IDs and values; keep real inputs and reports private. These checks do not establish production correctness or clear any original private application family.

After publication, the workflow's manual dispatch runs `public_download.py` on Windows and Ubuntu against the actual public release assets. The release is complete only after both public-download jobs pass.

See [release review](REVIEW.md) and [release notes](RELEASE.md).
