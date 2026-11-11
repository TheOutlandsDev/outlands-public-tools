# Public Release Audit

Offline pattern review of an explicitly selected stable text export. Findings
omit matched snippets, while inventories/reports retain relative names, sizes,
hashes and line numbers. **A clear-looking result is not privacy, rights or
software-safety clearance.** Keep actual exports, marker controls, reports and
manifests private.

Download the **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-release-audit-v0.1.0),
extract into a fresh folder and follow [USAGE.md](USAGE.md). Keep
`release_audit.py` and `audit_windows.py` adjacent. Use Python **3.12–3.15**;
qualification selects 3.15.2 for that minor. Only the standard library is needed,
without pip packages, network, model or account. No interpreter, dependency
binary, actual export/marker/report, private original or raw log is bundled.

```text
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --report NEW_PRIVATE_REPORT_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --deny-file PRIVATE_MARKERS_JSON --report NEW_PRIVATE_REPORT_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --write-manifest NEW_PRIVATE_MANIFEST_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --manifest REVIEWED_PRIVATE_MANIFEST_JSON
```

Run from the extracted folder or select the script by explicit path. Outputs
must be new files under existing private parents outside the selected root.
Input code is not imported, built, launched or modified. Reads may affect OS
access metadata; Python caches are separate.

| Result | Exit | Meaning |
| --- | ---: | --- |
| `NO_PATTERN_FINDINGS` | 0 | No findings/errors in this selected scan and optional manifest comparison. |
| `REVIEW_REQUIRED` | 1 | Findings, incomplete observations or inventory drift require review. |
| `ERROR` / `AUDIT_INPUT_OR_OUTPUT_ERROR` | 2 | Handled argument/input/I/O failure; new output can remain unconfirmed. |
| `ERROR` / `AUDIT_INTERRUPTED` | 130 | Handled Windows interruption; new output can remain unconfirmed. |

Stdout contains a JSON summary of status, inventoried file count, rule counts
and errors. Reports include the full inventory/findings/exclusions/scope.
POSIX interruption behavior remains preserved; static help is separate.

## Patterns, private markers and manifests

Rules cover selected credential/key/assignment shapes, addresses, internal
hosts, URL credentials, user-home/UNC/rooted paths and literal private markers.
Loopback/documentation addresses and listed example-email domains are allowed
for fictional data. False positives and missed secrets/identifiers remain
possible. Private markers are literal, case-insensitive strings in content and
relative names, not semantic matching. Reports are not redacted or anonymous.

After independently reviewing the exact export, `--write-manifest` records
selected paths, byte lengths and SHA-256. The tool refuses to create a manifest
when findings/errors require review. `--manifest` detects inventory differences.
A manifest made from unreviewed data grants no approval. Someone able to replace
both content and manifest can produce a matching pair; no signature or
independent authenticity is established.

## Bounds and output limits

Selected exports are bounded to **20,000 encountered entries, 2 MiB/file and
64 MiB total**. Marker/manifest JSON controls are capped at **16 MiB**; Windows
encoded outputs have a **64 MiB per-output** ceiling. These are not total CPU,
memory, regex or elapsed-time quotas. Root `.git` is explicitly excluded.
Unknown/binary/archive/non-UTF-8, linked/reparse, sensitive-name and private/
runtime entries require review. Git history, tags/branches/release assets,
metadata/archive interiors, external links and software behavior are unscanned.
Only unnamed text data is inspected; streams, ACLs and topology are outside scope.

Use stable ordinary files and fully spelled trusted quiescent local parents.
Native Windows checks cover supported local paths, scoped handles, bounded
reads, identities, outside-root outputs and exclusive creation. Actual
report/manifest dangling-link coverage and any confined output correction are
recorded separately in [qualification](docs/QUALIFICATION.md). The detector,
CLI/POSIX behavior, report/manifest contracts and historical
[WINDOWS.md](docs/WINDOWS.md) remain the preservation boundary. Runtime hashes
identify reviewed release bytes during a run, without an assumed older-backend
equality claim.

Failed writes can leave partial or complete-looking unconfirmed output, even
with a parsed clear-looking status. Require the actual successful result and
inspect output privately. No automatic cleanup/rollback or atomic multi-output
transaction is provided. Parent ACLs and OS/Python govern permissions;
confidentiality is not audited. Sampled pathname/open/create checks have race
windows, not hostile-filesystem containment, universal deadlines,
live/cloud/remote-provider or power-loss guarantees.

## Use and evidence

[USAGE.md](USAGE.md) gives a fictional clean → private finding → manifest →
comparison → drift guide with complete JSON/exit outcomes and preservation of
existing input/control/report/runtime bytes. Use an external
[private workspace](docs/PRIVATE-WORKSPACE.md). User-owned Python/venvs do not
inherently require administrator access; respect device policy without bypasses.

Eight fresh extracted-ZIP Windows/Ubuntu Python lanes select 19 original shared
method bodies, 40 I/O methods and copied CLI consumers in no-pip/no-distribution
venvs. Actual versions/counts/skips/outcomes belong to release `VALIDATION.json`;
intended coverage is not a passing result. Historical evidence stays separate.

Selected original source is [MIT licensed](LICENSE), with retained notices and
AI-assisted preparation without exclusive-authorship claims. See
[provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and the [earlier review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-26-PUBLIC-AUDIT-WINDOWS.md).
[Report an issue](https://github.com/TheOutlandsDev/outlands-public-tools/issues)
with invented data and complete outcomes. Do not attach actual exports,
organization markers, private reports/manifests, personal paths or raw logs.
