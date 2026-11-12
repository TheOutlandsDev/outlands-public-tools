# Private workspace

Extract reviewed source into a fresh directory. Choose a separate existing,
user-owned private parent for Python environments, candidates/current trees,
controls, reports, stdout captures and qualification receipts:

```text
source/release-preflight-0.1.0/          selected source and examples
private/release-preflight/
  venv312/                            separate no-pip environment
  fictional_walkthrough.py            private copy of usage driver
  fictional-demo/                     new authored fixtures
  candidate/                          actual reviewed local payload
  current/                            actual selected current tree
  controls/                           independently reviewed manifests/specs
  reports/                            new private report names
  qualification/                      fresh extraction and sanitized receipts
```

Keep `preflight.py` and `preflight_windows.py` adjacent. Select Python, command,
candidate, controls and raw-byte pins explicitly. `plan` also requires current;
`launcher-check` requires a separate specification/pin. No environment source,
download, installation, update application, shell, process/service action or
candidate import/execution occurs. The only checker-owned write is an optional
new `--report`; caller capture/redirection has separate overwrite behavior.

Use independently trusted manifest/spec pins. Hash agreement does not establish
an author, origin, safe executable, rights or deployment authority. An unchecked
file with a replaceable matching digest is not authenticated. Retain trusted
pins separately from the untrusted delivery; controls must be external to the
candidate. Fixtures deliberately use only invented material.

Candidate enumeration must match all listed files and required parent directories;
extra files/empty directories fail. Plan reads only selected current paths,
leaving unselected files uninspected/unselected. ADD/REPLACE/UNCHANGED observations
reserve nothing and retain no old payload bytes. Launcher success checks
structure/hash membership, not execution, arguments' meaning, permissions,
dependencies, availability or startability.

Reports must be new with existing parents outside the protected source tree and
candidate/current roots. Collection placement protects the collection; standalone
placement protects the enclosing runtime directory. The 0.1.0 scope assignment
corrects this distinction while preserving function bodies. Reports contain
relative filenames, hashes, sizes and recovery guidance. Actual controls,
launcher arguments, CLI history, results and native/library exceptions remain
private; fixed CLI errors are not a redaction service. Review a separate sanitized
export before sharing.

Require complete JSON and actual exit/status. Exclusive creation, complete-write
loops, flush and readback checks do not guarantee atomic success. Failed writes/
guards can retain partial or complete-looking unconfirmed new output. Keep it
for inspection; choose another new name for retry. No automatic cleanup,
overwrite, directory creation, rollback or application-consistent backup occurs.
Requested POSIX mode 0600 depends on OS/Python/ACL behavior and is not a
confidentiality/encryption promise.

Use canonical trusted local paths and quiescent trees. Windows checks lexical/
native components and held handles; POSIX uses available no-follow/nonblocking
flags and sampled ancestors/identities. Observed links/reparse/special/multi-link
files and sampled changes are refused. Selecting an ordinary Windows file does
not inspect/change all other streams. No atomic snapshot, writer denial,
hostile-filesystem boundary or I/O deadline is established. Drive rebinding,
mount aliases, remote/cloud/live/provider storage, ACL privacy, blocked I/O and
power loss remain outside acceptance. OS reads can affect access metadata or
use remote storage without a tool-owned network probe.

Controls are bounded at 1 MiB each, manifest files at 4,096, each payload at
256 MiB and aggregate payload at 1 GiB per pass, candidate entries at 8,192.
Relative names and launcher arguments have separate bounds in
[README.md](../README.md). Repeated passes are possible; these are not total
CPU/RAM/depth/deadline/storage quotas. A plan establishes no stopped state;
backups, maintenance authorization, separate application and recovery remain
the operator's responsibility.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. No pip distribution, account or model is needed.
Build/qualification outputs must be new private external paths with existing
parents. Publish reviewed source and sanitized actual validation only; exclude
real payloads/origins, configuration, arguments, paths, credentials, private
originals, binaries and raw diagnostics. See [USAGE.md](../USAGE.md),
[QUALIFICATION.md](QUALIFICATION.md), [PROVENANCE.md](PROVENANCE.md) and historical
[IO-SAFETY.md](../IO-SAFETY.md).
