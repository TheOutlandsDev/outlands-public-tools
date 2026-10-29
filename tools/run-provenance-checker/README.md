# OUTLANDS | Run Provenance Checker

Check declared run lineage, actual artifact pins and the public snapshot contract. Independent CLI/library; Python 3.12/3.13 standard-library runtime,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional walkthrough

From this tool's directory:

```text
python -B provenance.py --contract examples/provenance.json --manifest examples/manifest.json --snapshot examples/snapshot.json --policy examples/snapshot-policy.json --item code examples/code.txt --item configuration examples/configuration.json --item mapping examples/mapping.json --item preview examples/preview.json --item receipt examples/receipt.json --item reconciliation examples/reconciliation.json --item result examples/result.json --item schema examples/schema.json --item source examples/source.txt
```

The invented example returns PASS/exit 0. Source texts and JSON fixtures are
synthetic, with fixed invented identifiers and dates; no private original code,
records, templates, source mappings, operational configuration, user data, paths,
credentials or third-party assets are included. Original applications are not
opened, imported, modified or executed. Combined packages/browser apps are deferred.


## Declared lineage and snapshot contract

Library: `provenance.check(contract_raw, manifest_raw, snapshot_raw, policy_raw,
explicit_artifact_buffers)`. Supply exactly every manifest ID once. The manifest
uses `outlands-run-artifact-manifest-v1`, shared with the builder. Artifact bytes
are independently size/hash checked; code, configurations and evidence are opaque
buffers and are never imported or executed.

Exact contract: `format: outlands-run-provenance-v1`, run ID, raw manifest,
snapshot and snapshot-policy SHA-256 pins, `snapshot_bindings`, `steps`. Each
binding is `{id, artifact}`: snapshot item ID to a distinct run artifact ID.
Bindings must cover exactly all manifest artifacts classified input. The public
Snapshot Contract Checker validates snapshot/policy schemas, version, exact
pins, declared accounting and freshness using the **caller-supplied as-of time**.
It does not read a clock. Supported snapshot/policy formats are unchanged and
included in snapshot.py and the fictional examples.

Each step has unique ID, opaque `code_version`, unique nonempty `uses` and
`produces` ID lists. There are 1..16 steps. Step order is meaningful: an output
cannot be used before its producer or by its own producer. Each step uses exactly
one code artifact and at least one input/result artifact. Only result-role
artifacts may be produced, each exactly once. All artifacts must be used or
produced; unused mappings/configurations/evidence and unproduced results require
review. Unknown references, duplicate producers, forward references and cycles
cannot yield PASS. Any issue withholds the overall result.

These rules check the **declared graph**, not whether a calculation happened or
used the claimed inputs. Code versions are declarations, not verified Git refs.
Result values and evidence bodies are not semantically checked. An ingestion
reconciliation report included as evidence is pinned bytes, not independently
reconciled by this checker; run the receipt reconciler separately.

The public snapshot checker treats artifact record counts as declarations.
Matching false declarations may pass. This tool always retains
`record_counts_independently_verified: false`, `execution_verified: false` and
`source_authority_verified: false`. Hashes do not authenticate a replaced
manifest/policy/contract set. Supply review pins through a trusted process.
No target execution, update, database access, live discovery or publication.


## Shared limits, I/O and privacy

At most 16 selected artifacts, 4 MiB each and 16 MiB combined. IDs match
`[a-z][a-z0-9_-]{0,47}`; hashes are lowercase SHA-256. Manifest declared totals
also cannot exceed 16 MiB. JSON refuses duplicate keys, floats, nonfinite numbers,
invalid Unicode, excess depth (32)/nodes (100,000), strings over 4,096 characters,
integers beyond the supported bounds and unknown contract fields.

CLIs read explicit regular single-link files using the pinned public Windows/POSIX
guards. No path is read from a manifest, review, receipt or artifact body. Use
trusted quiescent files/parents. Selections are sequential bounded snapshots,
not an atomic capture or a guarantee against a hostile/privileged filesystem.
See [I/O boundaries](IO-SAFETY.md), [origins](ORIGINS.md), [validation](VALIDATION.md).

Output is private ASCII JSON on stdout, or `--out` creates a **new external report**
under an existing parent. Source-tree output and overwrite are refused; no
directory is created. Failed writes can retain partial/unconfirmed output. No
automatic cleanup or same-path retry; choose a new path after private inspection.
Windows inherits parent ACLs, without a confidentiality guarantee. Shell stdout
redirection does not inherit these guards. Reports, symbolic IDs, public-name
proposals, counts, hashes and relationships can still disclose private information.
Hash agreement and path omission do not anonymize an artifact or authorize sharing.

Exit codes: 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Errors
omit supplied values and paths. No source/environment discovery, live query,
process execution or target action occurs. Read each tool's specific evidence
limits above. Parser bounds are not OS resource quotas or an execution sandbox.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
