# OUTLANDS | Run Artifact Manifest Builder

Build a path-free manifest of explicit selected artifact bytes. Independent CLI/library; Python 3.12/3.13 standard-library runtime,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional walkthrough

From this tool's directory:

```text
python -B artifacts.py --selection examples/selection.json --item code examples/code.txt --item configuration examples/configuration.json --item mapping examples/mapping.json --item preview examples/preview.json --item receipt examples/receipt.json --item reconciliation examples/reconciliation.json --item result examples/result.json --item schema examples/schema.json --item source examples/source.txt
```

The invented example returns PASS/exit 0. Source texts and JSON fixtures are
synthetic, with fixed invented identifiers and dates; no private original code,
records, templates, source mappings, operational configuration, user data, paths,
credentials or third-party assets are included. Original applications are not
opened, imported, modified or executed. Combined packages/browser apps are deferred.


## Manifest construction

Library: `artifacts.build(selection_raw, {'symbolic-id': artifact_bytes})`.
Selection has exact fields `format: outlands-run-artifact-selection-v1`, `run_id`
and `artifacts` containing unique `{id, role}` objects. All IDs use the shared
identifier subset. Supply every selected ID once; missing/extra bindings fail.
Roles are input, mapping, schema, configuration, code, result or evidence. They
are caller classifications, not content inspection or proof of an artifact's role.

The result contains `manifest`, with `format: outlands-run-artifact-manifest-v1`,
the run ID and sorted `{id, role, bytes, sha256}` artifacts. Byte lengths/hashes
come from the supplied buffers. Empty bytes and identical bytes under distinct
IDs are allowed. File paths, original basenames, times and host details are not
recorded. Inputs are not executed, parsed as programs or scanned for secrets.

`manifest_sha256` pins the exact **canonical embedded manifest** bytes:
`toolkit.encode(result['manifest'])`. The `--out` file is a build report containing
that manifest, not a bare manifest. To save its manifest separately with the
same protection, a trusted caller can use:

```python
import artifacts
import toolkit

report = artifacts.build(selection_bytes, explicit_artifact_buffers)
toolkit.write_new(new_external_filename, toolkit.encode(report['manifest']))
```

This serialization sorts keys, uses compact separators and ASCII JSON, and
appends one LF. A differently serialized bare manifest needs a new raw-byte pin.
The supplied fictional provenance example uses that canonical form. No signature,
origin authentication, atomic multi-file capture or publication approval is added.
The manifest may reveal sensitive IDs, sizes, hashes and relationships despite
being path-free; keep it private unless separately reviewed.


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
