# Annotation Geometry 4 source bundle

This source-only bundle contains four already public MIT tools: annotation manifest checks, polygon geometry checks, bounding box conversion, and annotation export handoff checks. It is separate from Toolkit 0.9.0 and the other source bundles.

The [exact selection](plan.json) pins public source commit `fcb54da575cc1866489d432390c460155763ce32`. The builder takes only 73 selected Git blob files. Its ZIP adds a neutral README and member hash manifest; `SHA256SUMS.txt` is separate. ZIP timestamps and permissions are fixed synthetic values. No Git history, runtime, user profile, private instance, local configuration, image assets, or private source is included. MIT licenses retain public TheOutlandsDev attribution.

## Build and check

From a complete Git checkout with Python 3.12/3.13, choose a new external output directory that already exists:

```text
python -B downloads/annotation-geometry-4/build.py --output NEW_EXTERNAL_DIRECTORY
python -B downloads/annotation-geometry-4/verify.py --archive NEW_EXTERNAL_DIRECTORY/outlands-annotation-geometry-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
python -B downloads/annotation-geometry-4/accept.py --archive NEW_EXTERNAL_DIRECTORY/outlands-annotation-geometry-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
```

The pinned ZIP SHA-256 is `9f175d61b3e4573d211241d0e1d526f1281485dc89a78a478fc3ecb06dd83ac9`. Verification checks every member path, byte hash and archive metadata. Fresh extraction runs four source-manifest checks and four fictional CLI examples, all returning `PASS`. Hosted Windows/Ubuntu builds on Python 3.12/3.13 must match byte for byte. These tools inspect supplied declarations; they do not read image assets, repair polygons, edit annotations, or export datasets. Reports can contain supplied IDs and coordinates; keep real inputs and reports private. These checks do not establish annotation quality or clear any original private application family.

After publication, the workflow's manual dispatch runs `public_download.py` on Windows and Ubuntu against the actual public release assets. The release is complete only after both public-download jobs pass.

See [release review](REVIEW.md) and [release notes](RELEASE.md).
