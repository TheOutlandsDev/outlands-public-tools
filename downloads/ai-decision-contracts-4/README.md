# AI Decision Contracts 4 source bundle

This source-only bundle contains four already public MIT tools: prompt contract comparison, label-mapping checks, score-abstention policy checks, and candidate evaluation gate planning. It is separate from Toolkit 0.9.0 and the other source bundles.

The [exact selection](plan.json) pins public source commit `6bdb1664753b242e80f10166dda1b5a12b406a6b`. The builder takes only 69 selected Git blob files. Its ZIP adds a neutral README and member hash manifest; `SHA256SUMS.txt` is separate. ZIP timestamps and permissions are fixed synthetic values. No Git history, runtime, user profile, private instance, local configuration, or private source is included. MIT licenses retain public TheOutlandsDev attribution.

## Build and check

From a complete Git checkout with Python 3.12/3.13, choose a new external output directory that already exists:

```text
python -B downloads/ai-decision-contracts-4/build.py --output NEW_EXTERNAL_DIRECTORY
python -B downloads/ai-decision-contracts-4/verify.py --archive NEW_EXTERNAL_DIRECTORY/outlands-ai-decision-contracts-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
python -B downloads/ai-decision-contracts-4/accept.py --archive NEW_EXTERNAL_DIRECTORY/outlands-ai-decision-contracts-4-1.0.0.zip --checksums NEW_EXTERNAL_DIRECTORY/SHA256SUMS.txt
```

The pinned ZIP SHA-256 is `591c0a9952ec4865aeac15b8db4e89902dee8eb9adb480a8898a346bfb97b7e4`. Verification checks every member path, byte hash and archive metadata. Fresh extraction runs four source-manifest checks and four fictional CLI examples, all returning `PASS`. Hosted Windows/Ubuntu builds on Python 3.12/3.13 must match byte for byte. These tools inspect supplied declarations; they do not render prompts, relabel records, run model inference, or deploy candidates. Reports can contain supplied IDs and values; keep real inputs and reports private. These checks do not establish model quality or clear any original private application family.

After publication, the workflow's manual dispatch runs `public_download.py` on Windows and Ubuntu against the actual public release assets. The release is complete only after both public-download jobs pass.

See [release review](REVIEW.md) and [release notes](RELEASE.md).
