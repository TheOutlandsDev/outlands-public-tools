param([ValidateSet('preflight','run')][string]$Mode,[string]$ImageDigest)
$ErrorActionPreference='Stop'
$env:PATH="$env:SystemRoot\System32;$env:SystemRoot"
$root='C:\results'
trap {
  $failure=$_
  # Emit only bounded uppercase error codes, never report bodies or private paths.
  if(Test-Path -LiteralPath 'C:\private') {
    $codes=@(Get-ChildItem -LiteralPath 'C:\private' -Filter '*.log' -File -Recurse | Select-Object -First 12 | ForEach-Object {
      if($_.Length -le 65536) {[regex]::Matches((Get-Content -LiteralPath $_.FullName -Raw),'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b') | ForEach-Object {$_.Value}}
    } | Sort-Object -Unique | Select-Object -First 24)
    Write-Output ('CLEAN_DIAGNOSTIC_CODES='+($codes | ConvertTo-Json -Compress))
  }
  if(Test-Path -LiteralPath 'C:\private') {try {Copy-Item -LiteralPath 'C:\private' -Destination "$root\retained-private-run" -Recurse -ErrorAction Stop} catch {}}
  throw $failure
}
if($Mode -eq 'preflight') {
  $found=@('python','python3','py','pip' | ForEach-Object {Get-Command $_ -CommandType Application -ErrorAction SilentlyContinue})
  if($found.Count -ne 0){throw 'BASE_IMAGE_HAS_PYTHON_COMMAND'}
  foreach($key in @('HKLM:\SOFTWARE\Python','HKCU:\SOFTWARE\Python','HKLM:\SOFTWARE\WOW6432Node\Python')) {if(Test-Path -LiteralPath $key){throw 'BASE_IMAGE_HAS_PYTHON_REGISTRATION'}}
  $proof=@{status='PASS';image_digest=$ImageDigest;python_commands_absent=$true;python_registrations_absent=$true;bundle_mounted=$false;network='none';base_os_version=[Environment]::OSVersion.Version.ToString()}
  $proof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$root\base-proof.json" -Encoding UTF8
  exit 0
}
$base=Get-Content -LiteralPath "$root\base-proof.json" -Raw | ConvertFrom-Json
if($base.status -ne 'PASS' -or $base.image_digest -ne $ImageDigest -or $base.bundle_mounted){throw 'CLEAN_PREFLIGHT_REQUIRED'}
New-Item -ItemType Directory -Path 'C:\demo' | Out-Null
Get-ChildItem -LiteralPath 'C:\bundle' | Copy-Item -Destination 'C:\demo' -Recurse
New-Item -ItemType Directory -Path 'C:\private' | Out-Null
$launcher='C:\demo\Manufacturing Review Demo.cmd'
$health=(& $launcher --check --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $health.runtime -ne '3.14.10' -or !$health.isolated -or !$health.bundled_runtime){throw 'BUNDLED_HEALTH_FAILED'}
$run='C:\private\fresh run'
$result=(& $launcher --workspace $run --no-browser) | ConvertFrom-Json
$runExit=$LASTEXITCODE
if($runExit -ne 0 -or $result.status -ne 'PASS' -or $result.command_checks -ne 36 -or $result.expected_review_outcomes -ne 17){
  Write-Output ('CLEAN_LAUNCHER_EXIT='+$runExit)
  if($result.error -match '^[A-Z_]+$'){Write-Output ('CLEAN_LAUNCHER_CODE='+$result.error)}
  throw 'CLEAN_RUN_FAILED'
}
function Pins([string]$path) { @(Get-ChildItem -LiteralPath $path -File -Recurse | ForEach-Object {$_.FullName.Substring($path.Length)+':'+(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} | Sort-Object) }
$before=Pins $run
$refusal=(& $launcher --workspace $run --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 2 -or $refusal.error -ne 'NEW_PRIVATE_RUN_REQUIRED'){throw 'EXISTING_RUN_NOT_REFUSED'}
if(Compare-Object $before (Pins $run)){throw 'REFUSAL_CHANGED_OLD_RUN'}
$reopened=(& $launcher --open $run --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $reopened.status -ne 'PASS' -or (Compare-Object $before (Pins $run))){throw 'READ_ONLY_REOPEN_FAILED'}
$proof=@{status='PASS';image_digest=$ImageDigest;python_absent_in_pristine_base=$true;network='none';runtime=$health.runtime;bundled_runtime=$health.bundled_runtime;isolated=$health.isolated;command_checks=36;expected_review_outcomes=17;existing_run_refused_unchanged=$true;saved_run_reopened_without_writes=$true;report_sha256=(Get-FileHash -LiteralPath "$run\report.html" -Algorithm SHA256).Hash.ToLower();run_manifest_sha256=(Get-FileHash -LiteralPath "$run\RUN-MANIFEST.json" -Algorithm SHA256).Hash.ToLower();desktop_browser_tested_in_container=$false;physical_operations_performed=$false}
$proof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$root\clean-acceptance.json" -Encoding UTF8
Copy-Item -LiteralPath 'C:\private' -Destination "$root\retained-private-run" -Recurse
