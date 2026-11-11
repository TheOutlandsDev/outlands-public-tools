# Standalone download qualification

Source Inventory 0.1.0 is distributed as a reviewed source ZIP. Qualification
starts from fresh extracted bytes, not a checkout with an existing environment.
Actual interpreter versions, case counts, outcomes and skipped methods belong
to release `VALIDATION.json`. Planned lanes and older source-suite observations
are not a fresh passing result.

## Required lanes

Eight lanes cover Windows and Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each uses a new venv **without pip or installed distributions**, all three
adjacent runtime files and authored temporary inputs. No dependency install,
network, model or account is needed by the CLI/tests. Python/OS prerequisites
are supplied separately and retain their licenses.

The baseline comprises 124 inventory/tree/classification/native-safety methods;
[historical validation](VALIDATION.md) records the original 92 plus 32 and
earlier local skips. Another 26 copied-runtime process methods exercise the
real selected CLI files from an extracted copy. Fresh qualification must verify
discovery and report actual counts/outcomes rather than assume passing totals.
Zero discovered tests, wholly skipped suites or failures cannot qualify.

Hosted Windows qualification requires applicable native link/junction fixtures
to run and pass. The regression contract allows four Windows platform-only
skips plus explicit optional short-name-alias absence; POSIX skips 29 Windows-
native methods. Copied-runtime methods have their own explicit platform contract.
`tests/SKIP-CONTRACT.json` pins supported regression IDs/reasons. Every actual
skip must be recorded and is never a pass. Do not relax rejection or change
device policy/privilege to force a green result.

## What the checks establish

The source gate verifies the explicit reviewed allowlist/manifest, hashes,
sizes, Python/structured-data syntax, module-local documentation links and
selected privacy indicators. It is inventory/consistency evidence, not proof
of perfect secret detection, exclusive authorship or complete security review.

Source packaging requires selected bytes to match committed Git source. Sorted
members and fixed synthetic archive metadata produce deterministic source ZIP
bytes. All eight lanes also regenerate a reference package and compare both
ZIP and build-manifest bytes, then verify optimized-Python refusal in the two
helpers, `build.py` and `qualify.py`. Helpers use only the standard library and
refuse `-O`, `-OO` or `PYTHONOPTIMIZE` before assertions can be disabled.

Regressions and actual CLI fixtures cover default two-report compatibility,
hash/count/order, tree bounds/depth/exclusions/escaping, explicit partial-display
metadata, supplied-report hash consistency, literal first-match classification,
all-match/overlap/unmatched outcomes, output manifests, source preservation,
fresh writes, limits, native links/paths and failure/interruption behavior.
Inventory, classifier and Windows backend remain together in the copied runtime.

Tests must retain the distinction between exit 0 `COMPLETE_WITH_EXCLUSIONS`
and whole-tree completeness. A failed write can leave an unconfirmed,
complete-looking summary; its existence/hash agreement is not a success receipt.
Classifier success is `CLASSIFIED_SUPPLIED_ROWS`; unmatched/overlap outcomes
are valid user-policy results. Self-consistent supplied reports are not
authenticated source inventories or safety/license classifications.

## Reproduce with private outputs

From reviewed committed repository source:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Run these with the selected normal Python 3.12–3.15 interpreter. Both build
outputs must be new with existing parents; both come from the same reviewed
committed repository source. For qualification, `--packages` and
`--reference-build` select those existing artifact directories. Workspace and
report must be new absolute paths with existing parents. Qualification creates
its own fresh extraction/venv/test work outside the source module.

`--reference-build` is optional for a local run, but omitting it records no
deterministic-rebuild proof. Release acceptance requires `identical_zip` and
`identical_build_manifest` to be true. Actual CI executes both builds/reference
comparison in every lane; a local source test alone does not replace it.

Source ZIP/build metadata contain no interpreter, dependency binaries, actual
tree, real reports or raw diagnostics. Use an external
[private workspace](PRIVATE-WORKSPACE.md) for all artifacts/receipts. Run
`packaging/qualify.py --help` for option details. [USAGE.md](../USAGE.md) gives
end-user commands and the fictional inventory → tree → classify walkthrough.

No administrator privilege is inherently needed for user-owned portable
prerequisites and venvs. Device policy and OS support still apply; do not bypass
restrictions. Keep diagnostics, machine/account details, original helpers,
generated outputs, venvs and actual reports private. Publish the sanitized
structured validation summary with actual versions/counts/skips.

## Interpretation limits

Filename/time/hash metadata remains identifying even without absolute roots or
file bodies. Requested 0700/0600 modes depend on OS/Python/ACL behavior and do
not certify Windows confidentiality. Exclusions are convenience filters, not
complete secret detection or permission to publish a tree.

Observed path/handle/size/time checks have race windows. No atomic multi-file
snapshot, hostile-filesystem sandbox, universal I/O deadline, live-SMB acceptance
or power-loss recovery is established. Classification does not reopen original
bodies or validate optional tree metadata. A supplied CSV and summary hash can
be rewritten together. Read preserved [WINDOWS.md](WINDOWS.md),
[CLASSIFICATION.md](CLASSIFICATION.md), [PROVENANCE.md](PROVENANCE.md) and
[VALIDATION.md](VALIDATION.md); their historical matrices remain separate from
the standalone release's fresh results.
