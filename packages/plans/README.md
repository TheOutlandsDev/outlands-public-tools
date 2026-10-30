# Next source-only Toolkit inventory: preparation, not a release

[The candidate inventory](toolkit-v0.10.0-inventory.json) proposes **0.10.0** and
pins public source `ed7d1006960ab82d557bfb06977a6067fe4753f4`:

| Scope | Count |
| --- | --- |
| Candidate components | 199: 182 tools and 17 systems |
| Added since Toolkit 0.9.0 | 72 tools |
| Existing component source changed | 0 |
| Existing component source unchanged | 127 |
| Components removed | 0 |

This is a review snapshot, not an active packaging plan or a released asset.
GitHub can advance beyond this pin. The 72 additions cover maintenance, AI
decisions and datasets, visual annotations, routing, calibration, caching/retry,
configuration compatibility, workers, access policies, telemetry, API exchanges
and form/interaction contracts. Each row records its family, runtime requirements,
source-change class, changed-path count and README SHA-256. All comparison paths
come from Git trees, excluding local untracked files and private instances.

The inventory compares module paths under `tools/` and `systems/`; shared docs,
tests, packaging code and workflows need a separate exact-file review. The new
[software-quality exercise](../../workshops/software-quality-review.md) is a
proposed later packaging supplement and is not claimed inside this older source
pin. Its eventual reviewed packaging revision must be recorded separately.

## Reproduce the inventory

With the complete repository history available and Python 3.12/3.13 supplied
separately, run from the repository root:

```text
python -B packages/prepare_inventory.py --source-revision ed7d1006960ab82d557bfb06977a6067fe4753f4 --version 0.10.0 --output NEW_ABSOLUTE_JSON_PATH
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
