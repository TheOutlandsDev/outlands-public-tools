param([ValidateSet('preflight','run')][string]$Mode,[string]$ImageDigest)
$ErrorActionPreference='Stop'
$env:PATH="$env:SystemRoot\System32;$env:SystemRoot"
$root='C:\results'
$privateRoots=@('C:\private','R:\private')
trap {
  $failure=$_
  # Emit only bounded uppercase error codes, never report bodies or private paths.
  foreach($privateRoot in $privateRoots) {if(Test-Path -LiteralPath $privateRoot) {
    $codes=@(Get-ChildItem -LiteralPath $privateRoot -Filter '*.log' -File -Recurse | Select-Object -First 12 | ForEach-Object {
      if($_.Length -le 65536) {[regex]::Matches((Get-Content -LiteralPath $_.FullName -Raw),'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b') | ForEach-Object {$_.Value}}
    } | Sort-Object -Unique | Select-Object -First 24)
    Write-Output ('CLEAN_DIAGNOSTIC_CODES='+($codes | ConvertTo-Json -Compress))
  }}
  foreach($privateRoot in $privateRoots) {if(Test-Path -LiteralPath $privateRoot) {try {Copy-Item -LiteralPath $privateRoot -Destination (Join-Path $root ('retained-'+$privateRoot.Substring(0,1))) -Recurse -ErrorAction Stop} catch {}}}
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
New-Item -ItemType Directory -Path 'R:\private' | Out-Null
$launcher='C:\demo\Manufacturing Review Demo.cmd'
$health=(& $launcher --check --no-browser) | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $health.runtime -ne '3.14.10' -or !$health.isolated -or !$health.bundled_runtime){throw 'BUNDLED_HEALTH_FAILED'}
# Keep the original filesystem guards. A Windows container's overlay may not
# expose an ordinary local NT volume; select only storage accepted by the tool.
$storage=@();$chosen=$null
foreach($candidate in @(@{label='container-overlay';path='C:\private'},@{label='fresh-ntfs-mount';path='R:\private'})) {
  $probeInput=Join-Path $candidate.path 'storage-probe-input.json'
  Copy-Item -LiteralPath 'C:\demo\application\tools\resource-reservation-checker\examples\input.json' -Destination $probeInput
  $probeRaw=(& 'C:\demo\runtime\python.exe' -I -B 'C:\demo\application\tools\resource-reservation-checker\reservations.py' --input $probeInput)
  $probeExit=$LASTEXITCODE
  $probeRaw | Set-Content -LiteralPath (Join-Path $candidate.path 'storage-probe-private.log') -Encoding UTF8
  $probe=$probeRaw | ConvertFrom-Json
  $record=@{storage=$candidate.label;exit_code=$probeExit;status=$probe.status}
  if($probe.code -match '^[A-Z_]+$'){$record.code=$probe.code}
  $storage+=$record
  if($probeExit -eq 0 -and $probe.status -eq 'PASS' -and !$chosen){$chosen=$candidate}
}
Write-Output ('CLEAN_STORAGE_CHECKS='+($storage | ConvertTo-Json -Compress))
if(!$chosen){throw 'ORIGINAL_STORAGE_GUARD_REFUSED_ALL_CANDIDATES'}
$run=Join-Path $chosen.path 'fresh run'
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
$proof.storage=$chosen.label;$proof.original_storage_guard_passed=$true;$proof.storage_checks=$storage
$proof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$root\clean-acceptance.json" -Encoding UTF8
foreach($privateRoot in $privateRoots) {Copy-Item -LiteralPath $privateRoot -Destination (Join-Path $root ('retained-'+$privateRoot.Substring(0,1))) -Recurse}
