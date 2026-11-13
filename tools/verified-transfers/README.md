# Verified Transfers

Create externally pinned reviewed-source packages, or copy private stopped-state bytes into verified opaque bundles and restore them to a new destination. Python 3.12+, standard library only; Windows and Ubuntu qualification targets Python 3.12–3.15.2.

Download the [0.1.0 standalone source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/verified-transfers-v0.1.0), verify its SHA256SUMS and follow the complete [fictional usage guide](USAGE.md). The ZIP supplies source and tests, not Python, third-party packages, application binaries or real backup data. Keep `transfer.py` and `transfer_windows.py` adjacent. No administrator privilege, account login, pip installation or execution-policy change is part of the guide; actual permissions and workplace policy still apply.

## Reviewed source packages

Review a stable export and an exact inventory with schema `{"schema_version": 1, "inventory": [{"path": "relative/name", "size": 1, "sha256": "..."}]}`. Record the inventory's exact SHA-256 independently after privacy, ownership and license review. An inventory produced by [Public Release Audit](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/public-release-audit) is a candidate selection, not approval to publish.

`package --source EXPORT --manifest INVENTORY --expected-manifest-sha SHA --destination NEW_PACKAGE` copies selected text/source files into `payload`, then writes MANIFEST.json and MANIFEST.sha256. It verifies copied bytes and rechecks selected inputs. Format/name filters refuse unsupported content and private-looking paths; they do not establish secret clearance or intellectual-property rights. Payload files are never imported or executed.

## Private opaque handoffs

Use `backup --source PRIVATE_STATE --destination NEW_BUNDLE --confirm-stopped`, then `verify --bundle BUNDLE --expected-manifest-sha SHA`. Restore with `restore --bundle BUNDLE --destination NEW_RESTORE --expected-manifest-sha SHA --confirm-stopped`.

The stopped flag is an operator assertion, not an application/process check. Opaque bundles preserve relative filenames and bytes without parsing records, redaction, anonymization, encryption or compression. A verify pin is optional; restore requires the externally trusted manifest pin. The bundle's checksum detects accidental corruption and cannot authenticate an attacker-replaced manifest. Keep actual state, bundles, pins and summaries private.

## Destinations and safeguards

Every output destination must be new, have an existing parent, be disjoint from its source and lie outside the protected source boundary. In the literal collection layout `tools/verified-transfers`, that boundary is the collection root. A flat standalone copy protects its own runtime directory. This release's header repair preserves all transfer function/class bodies and the Windows native backend. It recognizes these layouts; it is not arbitrary Git-root discovery or a filesystem sandbox.

Existing files/directories are never replaced. Links, Windows reparse points and multiply linked regular files are refused. Bounded reads, sampled identities, noninheritable native handles, exclusive writes and read-back checks detect tested local I/O failures. Failures or interruption can retain partial private output; the tool performs no rollback or deletion. Inspect it privately and choose a different new destination for a retry.

Successful CLI results use exit 0 and include counts plus a manifest SHA-256. Handled refusals use exit 2 and fixed JSON with `TRANSFER_REFUSED_OR_FAILED` and `partial_destination: "retained"`; that field does not promise that a destination was created. Windows handled interruption uses exit 130 and `TRANSFER_INTERRUPTED`. POSIX/library interruption propagates. POSIX help may reflect the invoked path, and success data is not a redaction API.

The [qualification contract](docs/QUALIFICATION.md) describes 94 preserved original tests plus 30 copied-runtime methods per lane. Actual outcomes, named skips and archive/source pins are supplied by release VALIDATION.json and the build manifest. The historical [I/O notes](IO-SAFETY.md) retain earlier collection-layout wording and counts. See [provenance](docs/PROVENANCE.md), [private workspace guidance](docs/PRIVATE-WORKSPACE.md), [changes](CHANGELOG.md) and [license](LICENSE).

Use one operator with trusted stable local files. These checks do not provide atomic snapshots, hostile-filesystem isolation, hard I/O deadlines, ACL preservation or application-consistency proof. Mapped/network/cloud storage and real operational backups are outside qualification.
