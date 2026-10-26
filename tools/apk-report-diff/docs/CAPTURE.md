# Optional manual capture

The inspector only reads text. Capture is a separate action using an existing
trusted AAPT2 installation and APKs you are authorized to inspect. The official
[AAPT2 documentation](https://developer.android.com/tools/aapt2#dump) describes
`dump badging` as information extracted from the APK manifest. Producer versions
and syntax can vary; record the tool version privately and review coverage.

No capture command below is invoked by the inspector or acceptance tests. It
does not install an app or connect to a device, but it runs the separate AAPT2
binary against your selected APK. Keep raw APKs and reports private. Never attach
them to public issues without a separate rights/privacy review.

PowerShell 7, explicit existing private paths, fresh UTF-8 report file:

```powershell
$AaptPath = Read-Host 'Absolute path to your trusted aapt2.exe'
$ApkPath = Read-Host 'Absolute path to the APK you are authorized to inspect'
$ReportPath = Read-Host 'Absolute path for a new private text report'
$lines = & $AaptPath dump badging $ApkPath
if ($LASTEXITCODE -ne 0) { throw 'AAPT2 did not complete; report not created.' }
$bytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($lines -join "`n") + "`n")
$stream = [System.IO.File]::Open($ReportPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
```

The parent must already exist. `CreateNew` refuses an existing report. Review
capture errors in your local terminal; stderr is not an accepted metadata row.
Record another build in a different fresh report path. Do not concatenate
multiple packages into one input. Input limits still apply to manually captured
text. The synthetic examples are hand-authored fixtures, not proof that a live
SDK/APK capture was tested.

On a POSIX shell, use an existing private directory and shell no-clobber mode:

```sh
set -C
aapt2 dump badging /private/apk-review/authorized-build.apk > /private/apk-review/before.txt
```

Check the command's exit status before comparing. A failing command may leave a
partial/empty file; retain it privately as needed and use a new path for retries.
`aapt2` is resolved using your shell's PATH; select a trusted installation.
