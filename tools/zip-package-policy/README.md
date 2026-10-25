# OUTLANDS | ZIP Package Policy Verifier

Check whether a local ZIP has the files and literal text markers you expect,
without extracting or executing its contents. Useful for reviewing source
bundles, mod packages, release handoffs and configuration examples before sharing
or installing them. This is original [MIT-licensed source](LICENSE), written in
**PowerShell 7.2 or newer using standard .NET libraries**. No PowerShell modules, Pester,
Python, Windows-only commands or online services are required.

The public implementation generalizes an owner's local package-verification
workflow. The source is freshly authored; its generated Orchard example contains
no original package contents, private settings, device names or proprietary files.
See [provenance](docs/PROVENANCE.md).

## Try the fictional example

Clone or download [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools),
open a terminal in `tools/zip-package-policy`, and confirm `pwsh --version` reports
PowerShell 7.2 or newer. Use a private work directory outside the checkout, following the
[private workspace guide](../../docs/PRIVATE-WORKSPACE.md). Set `$privateWork` to an
existing absolute directory you control. Every generated destination below must
be new.

```powershell
pwsh -NoProfile -File ./Test-ZipPackagePolicy.ps1 -Help
pwsh -NoProfile -File ./examples/Make-Demo.ps1 -Destination "$privateWork/orchard-demo"
pwsh -NoProfile -File ./Test-ZipPackagePolicy.ps1 -ArchivePath "$privateWork/orchard-demo/package.zip" -PolicyPath "$privateWork/orchard-demo/policy.json" -ReportPath "$privateWork/orchard-report.json"
```

The check prints JSON with `status: "pass"` and exits **0**. The optional report is
created with exclusive creation, so a previous report cannot be overwritten. No
parent directories are created by the checker. You can omit `-ReportPath` and use
stdout. On Linux, the same PowerShell commands work with absolute `/home/...`
paths. Inputs must be normal local files under directories you control; paths
must be absolute, canonical and free of symbolic links/reparse points. UNC and
device paths are outside the supported scope. Do not aim this CLI at special
files, live system pseudo-filesystems or concurrently edited files.

## Write a policy

Save UTF-8 JSON outside the source checkout:

```json
{
  "schemaVersion": 1,
  "requiredMembers": ["README.txt", "settings/example.ini"],
  "allowedMembers": ["README.txt", "settings/example.ini"],
  "forbiddenMembers": ["private.env"],
  "limits": {"maxEntries": 100, "maxTextBytes": 32768},
  "textRules": [
    {
      "member": "settings/example.ini",
      "containsAll": ["[demo]", "mode=preview"],
      "containsNone": ["mode=production"]
    }
  ]
}
```

Member and marker comparisons are **case-sensitive ordinal literal comparisons**.
`.*` means those two characters, never a regular expression or script. A marker
may occur anywhere; this does not parse INI/JSON syntax or prove that a command
will execute. Required/allowed/forbidden member lists refer to files; directory
records are checked for safe structure but do not need to appear in those lists.
Without `allowedMembers`, extra files are permitted. An empty allowed list denies
every file. `schemaVersion` is the only mandatory field; a minimal policy still
performs bounded structural/name checks. Duplicate JSON fields, unknown fields,
contradictory requirements and wrong types fail closed.

You may add `expectedSha256` (64 hexadecimal characters) and `expectedSize` (bytes)
from an independently trusted publisher. The tool computes the SHA-256 of the
same bounded in-memory snapshot it inspects. A matching hash verifies equality
with the supplied digest; it does not establish the publisher's identity or rights.
The [format reference](docs/FORMAT.md) defines every field, bound and result.

## Results and limitations

| Exit | Result | Meaning |
| --- | --- | --- |
| 0 | `pass` | All supported requested checks completed with no findings. |
| 1 | `findings` | Inspection completed and policy mismatches were found. |
| 2 | `error` | Invalid/unsupported input, exceeded bound, unsafe structure, unreadable text or report-write failure; inspection is incomplete. |

Findings identify missing, forbidden and unexpected members, hash/size mismatches
and missing/present literal markers. Errors return a code without echoing a
filesystem path or exception. An input or inspection failure does not write a report; stdout is the
error record. A report write failure after creating the new file may leave a
partial new output; existing reports are untouched. Keep the process exit status when
using it in a pipeline.

The initial scope is single-disk ZIPs using stored/deflated entries and ASCII or
UTF-8 member names. ZIP64, encryption, other compression methods, trailing data,
prepended self-extracting executables, invalid central/local header relationships,
portable name collisions and special-file entries are rejected. The checker
preflights metadata counts before opening the .NET ZIP reader. It rejects unsafe
names (including traversal, drive/absolute paths, backslashes, Windows reserved
names, trailing dots/spaces, control and Unicode format characters), duplicate
names, case/NFC collisions and file/directory conflicts.

It is **not a malware scanner or installer**. Only selected `textRules` members
are decompressed, with strict UTF-8 and byte limits. Other file bodies and CRCs
are not verified. Structural checks are bounded consistency checks, not a proof
that every ZIP implementation will interpret a file identically. It does not
validate digital signatures, executable safety, license ownership, application
configuration semantics or suitability for a device/game. A malicious writer
controlling the filesystem can race path checks, especially on Unix; operate on
stable copies in a private directory, not an adversarial filesystem. Special
files such as Unix FIFOs are unsupported and their type is not reliably enforced
by the portable .NET path checks. The CLI has no timeout around native file opens
or reads; a special file or unresponsive local filesystem can block. Its byte
bounds apply to supported ordinary stable files, not filesystem-operation timing.

The archive hard limit is **64 MiB**, policy **1 MiB**, central directory **8 MiB**,
entry count **4,096**, total declared unpacked size **256 MiB**, per-member declared
size **64 MiB**, selected text per member **256 KiB** and total text **1 MiB**.
Policies may reduce these limits, never raise them. Larger archives need another
tool or a separately reviewed future extension.

## Privacy and tests

The tool makes no network requests and changes no inputs. Reports omit absolute
input paths and text bodies, but include a package hash and policy/member names
for findings. Those can identify private projects. Review policies and reports
before sharing; neither belongs in a public repository by default.

```powershell
pwsh -NoProfile -File ./tests/Run-Tests.ps1 -WorkRoot "$privateWork/zip-policy-tests"
```

The custom assertion harness uses generated ZIPs and policies only. It verifies
policy behavior, malformed inputs, safety bounds, fresh report writes and
unchanged source hashes. It retains generated evidence in the explicitly chosen
new directory. See [validation details](docs/VALIDATION.md). The main script has no
dependency on the test harness or demo generator.

## Bugs, improvements and suggestions

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=zip_policy_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=zip_policy_suggestion.yml).
Include OS, PowerShell version, exit status and a small fictional reproduction.
Do not upload real private ZIPs, credentials, copyrighted game assets or personal
reports. New formats, clearer findings and portability suggestions are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md).
