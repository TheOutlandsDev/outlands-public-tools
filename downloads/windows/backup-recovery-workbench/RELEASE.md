# Backup & Recovery Workbench — portable Windows x64

Download `backup-recovery-workbench-0.1.0-windows-x64.zip`, compare its SHA-256
against `SHA256SUMS.txt`, Extract All, and open **Recovery Demo.cmd**. CPython
3.14.10, SQLite, the unchanged focused application source and licenses are included.
No Python installation or administrator access is required. The distribution is unsigned.

**Recovery Exercise.cmd** runs a new fictional instance: snapshot three files
totaling 39 bytes, change its invented CSV from count 3 to 9, recover the original
count 3 into a new folder, then refuse a damaged snapshot copy with
`SNAPSHOT_CONTENT_MISMATCH`. Independent file comparisons verify that the original
snapshot, changed source and previous restore remain intact. Failed jobs stay
recorded. A repeat run gets a fresh exercise directory; existing instances are refused.
The exercise wrapper intentionally changes only its own fictional source CSV.
The original application's copy and restore operations never modify source contents.

The source is fixed at `4ac04985ff6a914095503f4f9a63c67806e57a50` and its published
source ZIP SHA-256 is `b5032e817b1e861f617f5a5fbcd45b84217f26add90977586bafa4b9b34f7747`.
Both Windows and Ubuntu build the Windows package from identical pinned inputs;
ZIPs and receipts must match byte for byte. The publisher requires actual fresh
Windows extraction, bundled-runtime checks, original core checks, CMD launcher
exercise, browser recovery, persistence, mismatch refusal, narrow layout and shutdown.
Consult `acceptance.json` and the corresponding Actions run for observed results.
The three JPEGs are actual Windows Chromium captures using only invented fixtures.
Their hashes and capture scope are recorded in `acceptance.json`; runtime journals,
tokens, local paths, input folders, databases and raw logs are not release assets.

State lives outside the extracted package in Windows local application data or an
explicit private workspace. Demo state persists and is never automatically reseeded.
No real backups, employer material, operational source mappings, credentials or user
files are included. Existing source releases, Toolkit 0.4.0 and other Windows bundles
remain independent downloads. The source application's original Python 3.12/3.13
qualification remains distinct from the bundled Python 3.14.10 Windows qualification.

This bounded quiescent copy format does not create atomic live snapshots, hot database
backups, permission/timestamp/alternate-stream restoration, encryption, signatures,
scheduling or automatic deletion. Retention is advisory. An index backup excludes
snapshot payload bytes. Preserve complete snapshot folders and independently trusted
manifest pins. Hashes are integrity comparisons, not signed attestation or proof of
power-loss, storage-hardware, hostile-filesystem or production recovery readiness.
