# Private workspace

Keep saved logs, generated fixtures, reports, packages, downloaded runtimes and
qualification evidence outside the source folder. Use an ordinary canonical
absolute directory you control on trusted local storage, without linked or
reparse-point ancestors. For fictional practice, run this in PowerShell:

```powershell
$privateWork = Join-Path ([IO.Path]::GetTempPath()) ("ffmpeg-log-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $privateWork | Out-Null
```

If your temporary directory has linked ancestors, choose an ordinary local
directory instead. Use a new demo/test destination and new report filename for
each run. The destination's parent must already exist. The inspector itself
does not create directories or overwrite files; its demo/test helpers create
only the explicitly requested new destination. A failed new report write may
leave a partial file.

Stop the log writer and inspect a stable ordinary copy. Native file operations
have no tool-enforced timeout; special files and unresponsive filesystems are
unsupported. Path checks do not prevent every adversarial filesystem race.

Real logs may contain private paths, media URLs, credentials, device names and
recording details. Reports omit raw lines and names but retain exact hashes,
sizes and numerical patterns that can still identify a log. Keep both private
until separately reviewed. This directory choice neither encrypts nor sanitizes
them. Use persistent private storage with suitable access and backup arrangements
for actual work, and authored fictional logs for public issues.

[Usage](../USAGE.md) · [Format](FORMAT.md) · [Qualification](QUALIFICATION.md)
