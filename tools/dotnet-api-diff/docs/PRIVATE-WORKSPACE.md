# Private workspace

Extract the release source ZIP into a fresh source directory. Choose a
separate user-owned private directory for SDKs, build outputs, trusted inputs,
test work, reports and qualification receipts. Keep these outside the source
checkout and public repositories. A fictional arrangement is:

```text
source/dotnet-api-diff-0.1.0/   reviewed public source only
private/api-diff/
  sdk10/                      separately obtained SDK 10.0.404
  sdk11/                      separately obtained SDK 11.0.100
  build10/                    generated net10.0 CLI, tests and fixture DLLs
  build11/                    generated net11.0 CLI, tests and fixture DLLs
  inputs/                     completed trusted assemblies selected by you
  reports/                    new private comparison reports
  qualification/              fresh extraction/build/test work and receipts
```

SDK/helper outputs and qualification workspace/report paths must be new, with
existing parents. Comparison report parents must exist, and report files must
be new. Existing reports and input assemblies are not overwritten. Failed
fresh output can be partial; inspect privately and choose another new filename.

Portable SDKs in user-owned folders do not inherently need administrator
access. Follow device policy and required OS-library prerequisites; do not
bypass restrictions. Before manual SDK use, apply [USAGE.md](../USAGE.md)'s
process-only global-tools `PATH`, ASP.NET certificate, telemetry and build-server
opt-outs. The SDK/qualification helpers already set child environments without
persisting these settings in a user profile or machine policy.

Use only trusted completed local build artifacts that you may inspect. Stop
producers first. Observed symlink/reparse components and UNC paths are refused;
portable checks cannot prove Unix regular-file type or prevent hostile path
replacement. The two immutable input snapshots are taken sequentially. Size/
time checks are sampled, not an atomic tree snapshot or adversarial sandbox.
Malformed/malicious metadata can crash or hang .NET readers despite file/work
limits. No timeout or process isolation is provided.

Reports omit wrapper input paths, bodies/resources and PDB paths but retain
API/assembly names, declarations and hashes. Metadata can contain identifying
or path-like text. CLI arguments, shell history and redirection can retain
private data. Protect actual assemblies/reports and review rights/privacy
before sharing. Omitted paths do not make a report anonymous.

The source release includes original fixture **source**. Generated fixture
DLLs, SDK archives/runtime files, compiled apps, originals, real assemblies,
real reports and raw diagnostics stay outside it. Public reproductions should
use authored fictional source. The MIT source license does not relicense
inputs, original private work or external prerequisites.
