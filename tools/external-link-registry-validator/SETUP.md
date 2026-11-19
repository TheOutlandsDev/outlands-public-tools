# Use the Offline External Link Registry Validator

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/external-link-registry-validator-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\external-link-registry-validator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\external-link-registry-validator-0.1.0.zip .\external-link-demo
Set-Location .\external-link-demo\external-link-registry-validator-0.1.0
```

Ubuntu shell

```sh
sha256sum external-link-registry-validator-0.1.0.zip
unzip external-link-registry-validator-0.1.0.zip -d external-link-demo
cd external-link-demo/external-link-registry-validator-0.1.0
```

## Validate the fictional registry

Run with Python 3.12 or 3.15. Use `python3` if that is the name of your
interpreter.

```text
python -I -B external_link_registry.py --input examples/registry.json
python -I -B external_link_registry.py --input examples/invalid.json
```

The first command prints `{"status": "valid", "count": 25}` and exits with
status 0. The second contains a percent-encoded session key with an empty
value. It exits with status 2 and writes a diagnostic on stderr.

## Supply your own saved registry

Use a regular UTF-8 JSON file without a byte-order mark. It can contain up to
256 KiB and must hold an array of 1 to 1,024 entries. Each entry is an object
with exactly two text fields, `label` and `href`.

Sort labels alphabetically using Unicode case folding. Duplicates are checked
by exact label equality. Each URL needs an HTTP or HTTPS scheme and a valid
host. The validator checks URL syntax and rejects embedded user information.
It also checks decoded, case-folded query keys for `ticket`, `token`,
`access_token`, `session`, and `sessionid`, including keys with blank values.

Diagnostics omit submitted labels, URLs, paths, and credential values. A
successful report gives the status and count. Validation is offline and
covers the saved definitions. URL availability is outside the report's scope.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

Read `VALIDATION.json` from the release for the Windows and Ubuntu
fresh-extraction results.
