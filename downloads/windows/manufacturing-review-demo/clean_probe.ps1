param([ValidateSet('preflight','run')][string]$Mode,[string]$ImageDigest)
$ErrorActionPreference='Stop'
$env:PATH="$env:SystemRoot\System32;$env:SystemRoot"
$root='C:\results'
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
$launcher='C:\demo\Manufacturing Review Demo.cmd'
$health=(& $launcher --check --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $health.runtime -ne '3.14.10' -or !$health.isolated -or !$health.bundled_runtime){throw 'BUNDLED_HEALTH_FAILED'}
$run="$root\fresh run"
$result=(& $launcher --workspace $run --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $result.status -ne 'PASS' -or $result.command_checks -ne 36 -or $result.expected_review_outcomes -ne 17){throw 'CLEAN_RUN_FAILED'}
function Pins([string]$path) { @(Get-ChildItem -LiteralPath $path -File -Recurse | ForEach-Object {$_.FullName.Substring($path.Length)+':'+(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} | Sort-Object) }
$before=Pins $run
$refusal=(& $launcher --workspace $run --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 2 -or $refusal.error -ne 'NEW_PRIVATE_RUN_REQUIRED'){throw 'EXISTING_RUN_NOT_REFUSED'}
if(Compare-Object $before (Pins $run)){throw 'REFUSAL_CHANGED_OLD_RUN'}
$reopened=(& $launcher --open $run --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $reopened.status -ne 'PASS' -or (Compare-Object $before (Pins $run))){throw 'READ_ONLY_REOPEN_FAILED'}
$proof=@{status='PASS';image_digest=$ImageDigest;python_absent_in_pristine_base=$true;network='none';runtime=$health.runtime;bundled_runtime=$health.bundled_runtime;isolated=$health.isolated;command_checks=36;expected_review_outcomes=17;existing_run_refused_unchanged=$true;saved_run_reopened_without_writes=$true;report_sha256=(Get-FileHash -LiteralPath "$run\report.html" -Algorithm SHA256).Hash.ToLower();run_manifest_sha256=(Get-FileHash -LiteralPath "$run\RUN-MANIFEST.json" -Algorithm SHA256).Hash.ToLower();desktop_browser_tested_in_container=$false;physical_operations_performed=$false}
$proof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$root\clean-acceptance.json" -Encoding UTF8
