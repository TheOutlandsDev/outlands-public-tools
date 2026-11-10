# Private workspace

Use an ordinary absolute directory you control on trusted local storage, outside
the source folder and without linked ancestors. For fictional practice:

```powershell
$privateWork = Join-Path ([IO.Path]::GetTempPath()) ("zip-policy-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $privateWork | Out-Null
```

Use a new demo destination and new report filename for each run. The output
parent must already exist. Real policies/reports can identify a project through
member names and hashes even without paths or file bodies. Keep them private;
this directory choice does not encrypt or sanitize them. For actual work use
persistent private storage with suitable access and backup arrangements.
