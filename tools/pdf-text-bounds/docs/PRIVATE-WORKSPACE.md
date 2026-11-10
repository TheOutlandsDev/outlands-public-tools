# Private workspace

Keep authored practice fixtures, environments and reports outside the source
folder on ordinary trusted local storage. In PowerShell, create a new directory:

```powershell
$privateWork = Join-Path ([IO.Path]::GetTempPath()) ("pdf-demo-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $privateWork | Out-Null
```

In a POSIX shell, use `PRIVATE_WORK="$(mktemp -d)"`. Keep the variable in that
terminal. Check that it is an absolute local path with no linked ancestors.
For actual work choose a persistent private directory with suitable access
and backup arrangements. Geometry and hashes can identify a document even
without its text. This path choice does not encrypt or sanitize reports.
