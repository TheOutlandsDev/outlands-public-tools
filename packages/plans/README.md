# Next source-only Toolkit inventory: preparation, not a release

[The candidate inventory](toolkit-v0.10.0-inventory.json) proposes **0.10.0** and
pins public source `7d798cb3f0240c57e74a3f7b8ea3f04002592a2d`:

| Scope | Count |
| --- | --- |
| Candidate components | 203: 186 tools and 17 systems |
| Added since Toolkit 0.9.0 | 76 tools |
| Existing component source changed | 0 |
| Existing component source unchanged | 127 |
| Components removed | 0 |

This is a review snapshot, not an active packaging plan or a released asset.
GitHub can advance beyond this pin. The 76 additions cover maintenance, AI
decisions and datasets, visual annotations, routing, calibration, caching/retry,
configuration compatibility, workers, access policies, telemetry, API exchanges,
form/interaction contracts and declared quote pricing. Each row records its family,
runtime requirements, source-change class, changed-path count and README SHA-256. All comparison paths
come from Git trees, excluding local untracked files and private instances.

The inventory compares module paths under `tools/` and `systems/`; shared docs,
tests, packaging code and workflows need a separate exact-file review. The new
[software-quality exercise](../../workshops/software-quality-review.md) is a
available at this source pin, but this component inventory does not qualify its
packaging or execution. The eventual reviewed packaging revision and exact shared
supplement membership must be recorded separately.

The [earlier 199-component inventory](https://github.com/TheOutlandsDev/outlands-public-tools/blob/b22f3d91cb4156f277da98130d6f0af715e5d766/packages/plans/toolkit-v0.10.0-inventory.json)
remains available at its immutable Git revision. This refresh adds only Price Book
Contract Checker, Quote Line Pricing Checker, Quote Total Reconciler and Quote
Pricing Scenario Comparator; all earlier component rows and README hashes agree.

## Reproduce the inventory

With the complete repository history available and Python 3.12/3.13 supplied
separately, run from the repository root:

```text
python -B packages/prepare_inventory.py --source-revision 7d798cb3f0240c57e74a3f7b8ea3f04002592a2d --version 0.10.0 --output NEW_ABSOLUTE_JSON_PATH
```

Choose a new output filename under an existing trusted private directory. Compare
its bytes or SHA-256 with this checked-in JSON. Use `Get-FileHash -Algorithm SHA256`
on Windows or `sha256sum` on Linux. To inspect any README independently, read its
Git blob at the exact source pin and SHA-256 the raw bytes; a Windows working-tree
checkout may use different line endings. A changed source revision requires a new
review and inventory; do not overwrite the prior evidence or silently reuse its
counts. A checksum alone does not authenticate an executor or publisher.

## Before a future publication

1. Review rights, privacy, exact source membership and changes after this pin.
2. Prepare the explicit package plan, source pin and separately reviewed shared
   guides, runner and packaging supplements. Do not edit old release assets.
3. Run packaging and component checks, then fresh source-archive exercises on
   Windows and Ubuntu. Supply each required runtime separately.
4. Compare independently built archives, exact members, manifests and checksums.
5. Publish a new named release only after those checks; verify fresh public
   downloads before changing the active catalog pointer and portfolio links.

No new ZIP, release tag or checksum for a built candidate is claimed here. The
active release stays **Toolkit 0.9.0 / 127 components**. Existing Windows bundles
keep their versions and evidence. The manufacturing Windows demo remains outside
this inventory and pending its separate clean-machine acceptance in
[PR #76](https://github.com/TheOutlandsDev/outlands-public-tools/pull/76).
