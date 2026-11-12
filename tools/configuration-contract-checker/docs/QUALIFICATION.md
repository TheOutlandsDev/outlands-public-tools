# Standalone download qualification

Configuration Contract Checker 0.1.0 is a reviewed source-only release.
Qualification starts from fresh extracted source and clean environments. Actual
versions/counts/outcomes/named skips belong to release `VALIDATION.json`;
selected coverage is not a passing result.

Eight lanes select Windows/Ubuntu Python **3.12, 3.13, 3.14 and 3.15.2**. New
venvs contain no pip or installed distributions; in-process imports select actual
extracted `config_check.py`. The CLI uses only its single script and stdlib/OS
APIs, without sibling tools or donors.

All 44 original method bodies, 129 total assertion calls and twelve local/shared
helper ASTs remain preserved. The total comprises 128 test-method assertions
and one assertion in the preserved reader-error helper. Explicit
`python-ast-fields-json-v1` encoding
retains full AST fields rather than interpreter-specific dump formatting;
within-version original/adapted equality remains required. Only needed shared
`Fixture`/`load` scaffolding is retained, without unrelated applications.
Runtime and all four examples retain exact baseline Git bytes.

A ROOT-relative original subprocess method uses an owned collection-shaped
fixture with an exact extracted runtime copy. Pre/post hashes must match;
qualification requires `runtime_mirror_test_only`/`runtime_mirror_verified`
true and `runtime_mirror_sha256` equal to runtime pins. The case must execute
without skip/failure. Independent copied CLI consumers use one copied script;
no duplicate runtime is shipped.

Another 26 process CLI methods select complete JSON/exit outcomes, native input
safeguards and input/runtime preservation. This selects **70/lane, 560 across
eight lanes**, comprising 352 original regression and 208 copied CLI cases.
Missing/duplicate IDs, changed originals/helpers, zero discovery, wholly skipped
modules, noncontract skips, failures and errors cannot qualify. Hosted applicable
native fixtures must run; local capabilities/platform skips need exact method/
reason contracts. Respect device policy; setup failure must not count as a CLI
refusal. Skips are not passes or substitutes for native hosted evidence.

The finite source gate checks inventory/manifest, hashes/sizes, syntax, local
links and selected privacy indicators. It is not perfect secret detection,
exclusive-authorship proof or blanket privacy/rights/security clearance. No
interpreter/dependency binary, actual configuration/result, private source or
raw diagnostic log is bundled.

Each hosted lane independently rebuilds committed source and compares **ZIP and
build-manifest bytes**, using sorted members/fixed synthetic archive metadata.
`build.py`/`qualify.py` refuse optimized Python (`-O`, `-OO`, active
`PYTHONOPTIMIZE`) before assertions can be disabled. CLI behavior is separate.

Preserved coverage includes strict schemas/scalar/resource bounds, Unicode exact
equality/code-point lengths, rule references, copied inputs, optional absence,
missing-before-invalid dependency precedence, unknown-key omission, field/rule
order, native input sampling, fixed errors and no target/network/process/output
writes. Both operands must be present and independently valid before comparison.
NOT_SUPPLIED is never PASS; blocked rules never silently pass. Four flags remain
false: `network_probed`, `programs_executed`, `configuration_modified`,
`runtime_verified`.

The unchanged runtime reads two selected inputs sequentially; per-file sampled
identities do not form an atomic input pair. Components are checked after
absolute normalization. No original-suffix guard is added; measured native
spellings are distinct from universal alias safety. Historical local 44/42/2
and collection Python 3.12/3.13 evidence remain separate from fresh qualification.
Actual fictional Windows probes on Python 3.12.7/3.15.2 accepted canonical,
leaf-dot, leaf-space and parent-dot forms for both contract/settings roles with
exit 0; parent-space returned 2/INPUT_PATH_INVALID, retaining input/runtime bytes.
These mixed observations provide no blanket original-component refusal claim.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and the same reviewed commit.
Qualification inputs must exist; workspace/report must be new absolute paths
with existing parents outside source. Keep work/receipts in an external
[private workspace](PRIVATE-WORKSPACE.md). A consumer may omit the reference,
honestly recording both `identical_*` flags false without independent Git-source
rebuild proof; hosted lanes require both true. Anonymous asset/source comparison
and fresh execution are separate evidence. [USAGE.md](../USAGE.md) supplies whole
fictional outcomes and input/extra/prior/runtime preservation checks.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. Actual contracts/settings/IDs/results, personal paths,
credentials, private source and logs remain private. Publish reviewed source and
sanitized actual validation only.

## Limits that remain

Each selected file is at most 64 KiB; fields/settings keys/rules are separately
bounded at 128, strings at 4096 code points, choices at 32 entries of at most
128 code points, integers signed 64-bit, IDs 40 characters and keys 64. Paths
have 4096-character/64-part bounds. These are not total CPU/RAM/JSON-depth/
deadline/storage quotas. Interruption/stdout failure can leave partial captures.

Passing constraints proves no application compatibility, dependency behavior,
security or runtime readiness. IDs/status relationships remain identifying even
with settings keys/values omitted. No privacy/IP/licensing/publication clearance
follows. Sampled reads are not atomic snapshots/pairs, deny-writer/race or
hostile-filesystem guarantees, arbitrary mount/drive alias, remote/live/provider,
universal I/O, ACL privacy or power-loss acceptance. Reads can affect access
metadata; caches/captures/tracebacks remain separate. See [README.md](../README.md)
and [PROVENANCE.md](PROVENANCE.md).
