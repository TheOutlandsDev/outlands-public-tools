# Use the Offline Incident Evidence Bundle Builder

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/incident-evidence-bundle-builder-v0.1.0).
Compare the calculated ZIP hash with its entry in `SHA256SUMS.txt` before
extracting into a fresh directory.

PowerShell

```powershell
Get-FileHash .\incident-evidence-bundle-builder-0.1.0.zip -Algorithm SHA256
Expand-Archive .\incident-evidence-bundle-builder-0.1.0.zip .\incident-demo
Set-Location .\incident-demo\incident-evidence-bundle-builder-0.1.0
```

Ubuntu shell

```sh
sha256sum incident-evidence-bundle-builder-0.1.0.zip
unzip incident-evidence-bundle-builder-0.1.0.zip -d incident-demo
cd incident-demo/incident-evidence-bundle-builder-0.1.0
```

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
if that is the name of your interpreter.

## Bundle the fictional reports

PowerShell

```powershell
$bundle = Join-Path (Split-Path -Parent (Get-Location).Path) 'fictional-incident.zip'
python -B -m opskit --home examples incident bundle --doctor doctor.json --inventory inventory.json --ports ports.json --include note.txt --output "$bundle" --json
```

Ubuntu shell

```sh
bundle="$(dirname "$PWD")/fictional-incident.zip"
python -B -m opskit --home examples incident bundle --doctor doctor.json --inventory inventory.json --ports ports.json --include note.txt --output "$bundle" --json
```

The command reads the saved reports and prints a receipt for the new ZIP.
Inside the ZIP, `manifest.json` records the final byte count and SHA-256 of
each diagnostic report and attachment. The receipt gives the ZIP's own SHA-256.

## Bundle selected files

Use `--home` to set a base directory for relative paths. Name all three saved
JSON reports with `--doctor`, `--inventory`, and `--ports`. Pass each optional
UTF-8 attachment with a separate `--include`. The builder only opens the
files you name. Save the output in an existing directory.

Each input and final member has a default limit of 2 MiB. Use
`--max-file-bytes` to lower that limit. The archive can contain up to 16
attachments. Invalid JSON, binary attachments, oversized input, and path
aliases are refused. An attachment's numbered archive name includes its
sanitized basename.

The builder masks recognized credential fields in JSON and matching assignment
lines in text. Review the member contents and names before sharing a bundle.
Other sensitive text can still be present.

The default mode protects an existing destination, including a file created
while the bundle is being assembled. This uses a hard link on the destination
filesystem. Use `--force` when you intend to replace an existing output file.
Input files remain untouched.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes fresh-extraction validation records for Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
