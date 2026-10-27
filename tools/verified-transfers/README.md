# Verified Source Packages and Private Data Handoffs

`transfer.py` uses only Python 3.12+ standard-library modules. It creates a new byte-for-byte directory package from an exact, pinned source inventory, or makes and verifies a private opaque file snapshot. It never imports or executes files from either input.

## Reviewed source package

First make a stable export containing only the files you intend to share. Review the export and the findings from [Public Release Audit](../public-release-audit/README.md); resolve or document every finding yourself. The audit tool's manifest is a candidate inventory, not a privacy or ownership approval.

```text
python tools/public-release-audit/release_audit.py --root EXPORT_DIRECTORY --write-manifest REVIEWED_INVENTORY.json
```

After reviewing the exact inventory bytes, record its SHA-256 separately. Then create the package in a new destination whose parent already exists and which is outside both the source tree and this repository:

```text
python tools/verified-transfers/transfer.py package --source EXPORT_DIRECTORY --manifest REVIEWED_INVENTORY.json --expected-manifest-sha RECORDED_SHA256 --destination NEW_PACKAGE_DIRECTORY
```

The pin binds packaging to the reviewed inventory bytes. Before publishing, review the produced `payload` again and run the release audit against that exact directory. The package contains only listed files plus `MANIFEST.json` and its checksum. The selected file list and content hashes are checked before and after copying; existing destinations are never replaced. A failure can leave a partial new destination, which is retained for inspection.

The source manifest must contain the exact schema written by Public Release Audit. The packager restricts entries to bounded text/source formats and rejects common private/runtime directory names, key/database formats, linked files, hard links, path traversal, duplicate/case-colliding names and unsupported content. These are filters, not secret detection or IP review. Ordinary text and filenames can still disclose private information. The caller must choose and review the exact export.

## Private opaque data handoff

This mode copies every regular file below an operator-selected data directory into a new verified package and can restore it to a new directory. It preserves file bytes and relative filenames; it does not inspect, redact, anonymize, encrypt, compress, or execute them. Database and application data may contain user records, credentials, configuration, logs or other sensitive material. Keep the source, bundle, manifests, restore and their parent directories private and outside the repository.

The confirmation flag is an operator assertion. The utility does not check whether an application or server is actually stopped, whether the destination is authorized, or whether the snapshot is valid for a particular application. Stop the application cleanly and verify its own backup/restore procedure separately.

```text
python tools/verified-transfers/transfer.py backup --source PRIVATE_STATE_DIRECTORY --destination NEW_PRIVATE_BUNDLE --confirm-stopped
python tools/verified-transfers/transfer.py verify --bundle PRIVATE_BUNDLE --expected-manifest-sha RECORDED_SHA256
python tools/verified-transfers/transfer.py restore --bundle PRIVATE_BUNDLE --destination NEW_RESTORE_DIRECTORY --expected-manifest-sha RECORDED_SHA256 --confirm-stopped
```

Record the manifest digest through a separate trusted channel. An internal checksum detects accidental changes but is not an authenticity proof; restore requires the separately recorded digest. The restore target must be new and is never overwritten. Partial destinations are retained on failure. The tool does not remove source data or old backups.

## Limits

- The source mode copies only an explicit hash-pinned inventory. It is not a complete project snapshot, content sanitizer, malware scan, or license/IP assessment.
- The data mode is for private, quiescent local trees. It has bounded file, count and byte limits; rejects links, reparse points, hard-linked files and database sidecars. It does not verify process state or filesystem ownership.
- Hash and identity checks detect common changes during reads and copies, but do not freeze a hostile or concurrently modified filesystem. Use trusted, stable source and destination parents.
- Manifests include relative filenames and hashes. Keep data manifests private because names and hashes can reveal information.
- POSIX permission requests are not equivalent to encryption. Effective permissions vary by platform. Windows/POSIX file handling is hardened with fictional fixtures; network/cloud providers, power-loss recovery, concurrent hostile writers and application-specific restore behavior remain unvalidated.
- A successful verification means the bundle matches its manifest and optional external pin; it does not establish where the data came from or that restoring it is safe.

See [I/O checks and platform limits](IO-SAFETY.md) and the
[current review](../../docs/BATCH-34-VERIFIED-TRANSFERS-IO.md). Windows requires
the adjacent `transfer_windows.py` in the existing layout. Native path rules
are stricter; bundle formats and pins are preserved. New files are read back;
partial or complete unconfirmed output stays private and is not removed.

See [Batch 7 review](../../docs/BATCH-7-REVIEW.md) for original provenance. MIT licensed; see [licensing](../../LICENSING.md).
