# Python 3.15 engine and CLI qualification

Python 3.15 removed `Path.is_reserved`. The Windows destination-name check now
uses `os.path.isreserved` when available and retains the original pathlib
fallback on Python 3.12. Path traversal, device names, alternate-stream colons,
control characters, wildcard characters and trailing dots/spaces remain refused.
The change does not alter transaction ordering, journal handling, content
verification, retained recovery copies or purge permissions.

The added filename regression checks reserved device aliases, invalid Windows
names and valid ordinary names without creating files. Existing tests exercise
verified moves, interrupted recovery, restoration without destination removal,
destination collisions, source/staging/destination mutation refusal, final purge
reverification, named-stream preservation and corruption detection, and unsafe
journal/state/link refusal. All data is generated in disposable fixture trees.

The local Windows 11/Python 3.15.2 full run discovered 116 methods: 99 passed,
14 were explicitly skipped, and three native symlink fixtures failed because
the current account lacks symlink privileges. These are retained failures, not
passes. No privilege, Developer Mode, service, firewall or security-policy
change was made to obtain a result. Move/recovery/restore/purge and named-stream
fixtures completed locally; the symlink variants require a capable test host.

The [platform workflow](../../../.github/workflows/file-mover-checks.yml) runs
Windows and Ubuntu on Python 3.12, 3.13 and 3.15.2. Native Windows features are
required: unavailable features fail, and missing named-stream execution fails
the original regression step. Consult the actual workflow result rather than
treating workflow presence or local partial evidence as full qualification.

The original package metadata remains `>=3.12.7,<3.13`. This is a source/CLI
compatibility lane; no wheel install, GUI, live SMB, original user-data move,
hostile concurrency, hardware failure or power-loss durability is qualified.
Purge remains destructive and requires verified retained data and destination;
a matching hash does not establish independent backup or storage durability.
