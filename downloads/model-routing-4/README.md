# Model Routing 4 source bundle

This source-only bundle contains four already public MIT tools: model capability checks, request routing plan checks, fallback chain checks, and inference receipt reconciliation. It is separate from Toolkit 0.9.0 and the other source bundles.

The [exact selection](plan.json) pins public source commit `9457426543b3fdcea0237b4023dce9279e3295ab`. The builder takes only 73 selected Git blob files. Its ZIP adds a neutral README and member hash manifest; `SHA256SUMS.txt` is separate. ZIP timestamps and permissions are fixed synthetic values. No Git history, runtime, user profile, private instance, local configuration, model weights, or private source is included. MIT licenses retain public TheOutlandsDev attribution.

## Build and check

From a complete Git checkout with Python 3.12/3.13, choose a new external output directory that already exists:

```text
python -B downloads/model-routing-4/build.py --output NEW_EXTERNAL_DIRECTORY
python -B downloads/model-routing-4/verify.py --archive NEW_EXTERNAL_DIRECTORY/outlands-model-routing-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
python -B downloads/model-routing-4/accept.py --archive NEW_EXTERNAL_DIRECTORY/outlands-model-routing-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
```

The pinned ZIP SHA-256 is `e2b9c15cd99dc5c1cdc9eb609c991439757db6be4010780969bd76954e9fe9b2`. Verification checks every member path, byte hash and archive metadata. Fresh extraction runs four source-manifest checks and four fictional CLI examples, all returning `PASS`. Hosted Windows/Ubuntu builds on Python 3.12/3.13 must match byte for byte. These tools inspect supplied declarations; they do not load models, probe providers, dispatch requests, or perform inference. Receipts are reconciled against declared plans and do not prove inference occurred. Reports can contain supplied IDs and values; keep real inputs and reports private. These checks do not establish routing quality or clear any original private application family.

After publication, the workflow's manual dispatch runs `public_download.py` on Windows and Ubuntu against the actual public release assets. The release is complete only after both public-download jobs pass.

See [release review](REVIEW.md) and [release notes](RELEASE.md).
