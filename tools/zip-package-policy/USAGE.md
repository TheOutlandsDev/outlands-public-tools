# ZIP Package Policy Verifier 0.1.0

Download the source ZIP, USAGE.md, VALIDATION.json, build-manifest.json and
SHA256SUMS.txt from the same release. Verify the complete listed hashes before
extracting: PowerShell `Get-FileHash -Algorithm SHA256 ./*.zip`; Ubuntu
`sha256sum -c SHA256SUMS.txt`. Compare every listed asset. Unpack into a directory
you control. The ZIP contains original MIT source, tests, documentation and
authored generators, with no runtime, PowerShell module, third-party binary,
actual package, generated ZIP or private policy/report.

The qualified runtimes are PowerShell 7.6.10 LTS and 7.7.0 stable on Windows x64
and Ubuntu x86-64. Obtain PowerShell separately from its official distribution.
Windows PowerShell 5.1 is insufficient. The CLI needs no Python, .NET SDK,
Pester, module installation or administrator privilege. Corporate device policy
may restrict script execution; these instructions do not change that policy.

Open PowerShell in the extracted `zip-package-policy-0.1.0` folder. Follow the
[private workspace guide](docs/PRIVATE-WORKSPACE.md), then run:

```powershell
pwsh --version
pwsh -NoProfile -File ./Test-ZipPackagePolicy.ps1 -Help
$demo = Join-Path $privateWork 'orchard-demo'
pwsh -NoProfile -File ./examples/Make-Demo.ps1 -Destination $demo
pwsh -NoProfile -File ./Test-ZipPackagePolicy.ps1 -ArchivePath (Join-Path $demo 'package.zip') -PolicyPath (Join-Path $demo 'policy.json') -ReportPath (Join-Path $privateWork 'report.json')
```

Use these same commands in PowerShell on Ubuntu, with ordinary absolute Linux
paths. Every demo destination and report file must be new. The expected result
is exit **0**, `status: "pass"`, and two files in the authored package. The report
contains the package hash, sizes and coverage. It omits source paths and text
bodies. It may include member names for findings; keep real reports private.

Exit **1** is a completed inspection with policy findings. Try changing a
required literal in a separate copy of the fictional policy, then run it with a
new report filename. Exit **2** is incomplete: invalid/unsupported input, resource
limit, unsafe archive structure, unreadable selected text or output failure.
Existing reports and both inputs are never overwritten. A failed new report
write can leave a partial new file; use the exit status and a fresh destination.

To apply a policy to your own stable trusted local ZIP, review
[the format](docs/FORMAT.md) and [README limits](README.md). `expectedSha256`
is useful only when the expected hash comes from a separately trusted source.
The tool does not extract, execute, install or repair package contents. It makes
no network requests. Inspection of unselected bodies/CRCs, authenticity,
malware safety, signature validation and application compatibility are outside
its scope. Supported archives are bounded single-disk stored/deflated ZIPs;
ZIP64/encryption/unsupported methods and unsafe names are refused.

Inputs must be completed ordinary files under trusted directories, not live,
linked, remote or special files. Portable path checks are not an adversarial
filesystem sandbox and do not reliably enforce every special-file type. There
is no native-open/read timeout or hard process RAM bound. Hostile races and
unresponsive local filesystems remain outside qualification.

Maintainers may run `pwsh -NoProfile -File ./tests/Run-Tests.ps1 -WorkRoot NEW_ABSOLUTE_PRIVATE_DIRECTORY`.
The original harness generates 60 checks and preserves its authored fixtures
for private inspection. Python 3.12-3.15 is required only for optional source,
build and qualification helpers. See [repeatable qualification](docs/QUALIFICATION.md),
[provenance](docs/PROVENANCE.md) and [runtime notices](THIRD-PARTY-NOTICES.txt).
