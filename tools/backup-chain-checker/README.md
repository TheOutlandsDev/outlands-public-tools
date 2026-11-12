# Offline Backup Chain Checker

Check a bounded JSON declaration of full and incremental snapshot relationships.
Python **3.12–3.15**, standard library only; qualification selects 3.15.2 for that
minor. Only the explicitly selected control file
is read; the checker writes JSON to stdout and creates no report or backup files.

`DECLARED_CHAIN_CONSISTENT` describes this format's declared relationships. It
does not prove that a backup exists, is complete, matches its parent, has intact
contents or can be restored. The checker performs no backup, restore, deletion,
storage scan, command generation or network probe. Real plans and results stay
private: even neutral IDs and dependency order can disclose an operational design.

## Standalone source release

Download the **0.1.0 source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/backup-chain-checker-v0.1.0),
extract into a fresh directory and follow [USAGE.md](USAGE.md). The CLI needs
only `chain_check.py`, without pip distributions, package installation, network,
model or account. No interpreter/dependency binary, actual backup/control/result,
private original source or raw diagnostic log is bundled.

```text
python -B chain_check.py --plan EXISTING_PRIVATE_PLAN_JSON
```

The explicit plan is required. There is no backup root, environment/default
plan, output writer, restore command or deletion switch. Capturing stdout is a
separate caller action and can overwrite a caller-selected capture. User-owned
Python/venvs do not inherently require administrator access; respect device
policy without bypasses.

The single runtime and four original fictional JSON examples retain exact
baseline Git bytes. Original path components are checked before absolute-path
normalization; this release adds no new suffix guard or graph semantics.
Historical evidence below remains separate from fresh standalone qualification.

## Fictional walkthrough

From the extracted module directory (or the collection module directory):

```text
python -B chain_check.py --plan examples/valid-chain.json
```

Exit **0**, `DECLARED_CHAIN_CONSISTENT`. The selected declared order is
`sample_full`, `sample_first`, `sample_second`. These are fictional IDs, not
filenames or commands. No backup application or content is required.

```text
python -B chain_check.py --plan examples/missing-parent.json
python -B chain_check.py --plan examples/cycle.json
python -B chain_check.py --plan examples/unrelated-broken.json
```

Each returns exit **1**, `REVIEW_REQUIRED`. Missing-parent and cycle examples
have an empty selected order. The unrelated-broken example has a consistent
selected chain and retains its three-ID order, but another declared branch has
a missing parent, so the overall result still requires review.

The four examples contain newly authored fictional metadata only. Keep real
input files, stdout and any privately saved reports outside the checkout. See
the [private workspace guide](docs/PRIVATE-WORKSPACE.md).

## Exact input contract

```json
{
  "schema_version": 1,
  "restore_point_id": "sample_first",
  "snapshots": [
    {"id": "sample_full", "series_id": "sample_series", "kind": "full", "parent_id": null, "sequence": 0},
    {"id": "sample_first", "series_id": "sample_series", "kind": "incremental", "parent_id": "sample_full", "sequence": 1}
  ]
}
```

All shown field sets are exact. The schema version is integer `1`; there are
1 to 256 snapshot declarations. IDs, series IDs and the selected restore-point
ID are ASCII tokens matching `[a-z][a-z0-9_-]{0,39}`. IDs must be globally unique;
duplicates are input errors before graph construction. `parent_id` is null or
the same token type; an absent referenced ID is a relationship issue. Sequence
is an integer from 0 through 1,000,000; booleans, floats and strings are refused.

Supported declarations are:

- A `full` snapshot has a null parent. It can start at any allowed sequence.
- An `incremental` snapshot has exactly one parent. That parent must exist,
  belong to the same series and have a strictly smaller sequence.
- Sequence values are unique within each series. Gaps and branches are allowed.
  Multiple full roots in one series are allowed with different sequences; a
  selected order follows only the declared parent links.
- Every parent-reference cycle is flagged, including self references and edges
  incorrectly declared on full snapshots. Descendants of a cycle are not cycle
  members, but their selected ancestry is blocked.

This is a fresh neutral convention, not an adapter for a vendor backup format.
Differential, deduplicated, multi-parent and reference-dependent storage beyond
this single-parent model are unsupported. Paths, endpoints, identities,
credentials, hashes, timestamps, sizes, commands and payloads have no fields.
Unknown fields, duplicate JSON keys, nonstandard numbers and invalid types are
refused; values are not coerced, expanded, guessed or repaired. A misleading
operator declaration cannot be detected from metadata alone.

## Issues and selected order

Snapshot result rows are sorted by ID. `issues` describes each snapshot's local
declaration, not its complete ancestry. The codes have this fixed order:

| Code | Meaning |
| --- | --- |
| `FULL_PARENT_NOT_NULL` | A full snapshot declares a parent |
| `INCREMENTAL_PARENT_NOT_SUPPLIED` | An incremental snapshot declares null |
| `PARENT_NOT_FOUND` | The declared parent is absent |
| `PARENT_SELF_REFERENCE` | A snapshot names itself as parent |
| `PARENT_SERIES_MISMATCH` | The parent belongs to another series |
| `PARENT_SEQUENCE_NOT_EARLIER` | The parent sequence is equal or later |
| `SEQUENCE_REUSED_IN_SERIES` | Multiple IDs claim one series/sequence pair |
| `DEPENDENCY_CYCLE` | The snapshot belongs to a parent-reference cycle |

All snapshots are reviewed, including those outside the selected ancestry. Any
local issue or blocked target makes the **overall** status `REVIEW_REQUIRED`.

`target` contains the selected ID, its separate status, fixed issues and
`declared_order`. A missing selected ID gives `RESTORE_POINT_NOT_FOUND`. Any
local issue along its ancestry gives `TARGET_CHAIN_BLOCKED` and an empty order;
no partial order is offered. Otherwise, `declared_order` lists only its full root
through the selected incremental in dependency order. A clean selected chain
can coexist with overall review for an unrelated broken branch.

Results omit sequences, series labels, parent fields, input paths and native
errors. They retain snapshot IDs, counts, issue codes and the selected dependency
order. Those results are private metadata, not anonymized output or deletion
authorization. All action/verification flags remain false. No actual backup
contents, ownership, encryption keys, signatures, application consistency,
compatibility, completeness, retention policy or restorability are verified.

Do not feed dependent snapshots into the separate
[Backup Retention Planner](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/tools/backup-retention-planner/README.md), which accepts
declared independent full snapshots only. A consistent chain here neither
changes that contract nor establishes a safe removal decision.

## CLI, input limits and filesystem boundary

`--plan CONTROL_JSON` is required. `--help` and `--version` are static. Exit
`0` means the overall declarations are consistent, `1` means review is required,
`2` means input/argument error and `130` means interrupted. Errors use fixed codes
without echoing supplied values, selected paths or native exceptions.

The UTF-8 control file is limited to 64 KiB; an optional UTF-8 BOM is accepted.
The reader requires an ordinary single-link file and ordinary ancestors with
usable file identities. It checks identity/size metadata before, during and
after a bounded read. Link/reparse forms, UNC/device forms, parent traversal,
drive-relative paths, Windows reserved names and trailing dots/spaces are
refused. Original path parts are checked before absolute-path normalization so
Windows cannot silently erase a refused trailing suffix.

Use trusted stable local files. Metadata checks are sampled, not an atomic
snapshot or hostile-filesystem sandbox. Mount aliases and hostile concurrent
replacement remain outside the guarantee. OS storage access can involve a
network filesystem even without an explicit network probe. A byte bound does
not interrupt blocked OS I/O. Formatted library exceptions can retain Python
source locations; the fixed CLI report is not a traceback anonymizer.

## Historical validation and provenance

```text
python -B -m unittest discover -s tests -p test_original_chains.py -v
```

The historical local Windows/Python 3.12.7 suite discovered 43 tests: 41 passed, two native
link operations were skipped. It includes all 1,296 four-node parent graphs
checked against a separate reachability oracle, 300 seeded valid forests,
permutation invariance, maximum depth, blocked ancestry, malformed JSON and
no-side-effect checks. A fresh process also runs a copy of the single script
outside the collection. Skips are not passes. The original collection workflow
targets Windows/Ubuntu with Python 3.12/3.13; historical counts are not current
standalone results. The original suite retains its collection filename;
the command above selects the preserved standalone adapter.

See the [batch review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-15-BACKUP-CHAINS.md) for historical publication
scope and evidence. No held original server/backup source, private inventory,
configuration or operational record was selected, read, copied or executed.
The control-file reader adapts this collection's public MIT retention-checker
pattern at commit `dd49bf02674394004111b6df37743dbf53c5d42d`, with the original-path
suffix validation added here. No third-party implementation or runtime is bundled.
Selected original code, tests, documentation and fictional examples use
[MIT](LICENSE), attributed to TheOutlandsDev.

## Standalone qualification and privacy

Eight fresh extracted-ZIP Windows/Ubuntu Python 3.12, 3.13, 3.14 and 3.15.2 lanes
select the 43 original regressions plus copied single-script CLI consumers in
no-pip/no-distribution venvs. Original method/assertion and eight helper ASTs
remain preserved using versioned canonical field encoding. Tests select the
actual extracted module/script directly; no runtime mirror, donor source or
duplicate checker is needed. Applicable hosted native fixtures must execute,
and any permitted local/platform skip needs an exact contract. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`, not
planned coverage. See [qualification](docs/QUALIFICATION.md).

[USAGE.md](USAGE.md) supplies isolated fictional graph declarations, complete
JSON/exit comparisons and input/extra/prior-output/runtime preservation. The
whole graph and selected target have separate review status; a clean selected
order can coexist with unrelated branch issues. No partial selected order is
offered when any selected ancestor is blocked.

All eight action/verification flags stay false: `filesystem_scanned`,
`backup_contents_read`, `metadata_verified`, `restore_performed`,
`deletion_performed`, `deletion_authorized`, `commands_generated` and
`network_probed`. IDs, issue relationships and declared order remain private
metadata. A consistent declaration does not verify content, independence,
authenticity, restorability or permission to remove anything. Source/input
reads may affect access metadata; byte/tree checks do not inspect every OS
property or establish confidentiality.

See [provenance](docs/PROVENANCE.md), [third-party notices](THIRD-PARTY-NOTICES.md)
and public [collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md).
Standalone preparation used AI assistance without exclusive-authorship claims.
Report issues with invented declarations and complete outcomes, excluding
actual backup identifiers, dependencies, source paths, credentials and raw logs.
