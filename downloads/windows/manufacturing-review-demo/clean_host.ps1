param([Parameter(Mandatory=$true)][string]$Packages,[Parameter(Mandatory=$true)][string]$Workspace)
$ErrorActionPreference='Stop'
if($env:GITHUB_ACTIONS -ne 'true' -or $env:GITHUB_REPOSITORY -ne 'TheOutlandsDev/outlands-public-tools' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted'){throw 'EPHEMERAL_GITHUB_RUNNER_REQUIRED'}
$Workspace=[IO.Path]::GetFullPath($Workspace)
$tempRoot=[IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\')+'\'
if(!$Workspace.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase) -or $Workspace -match '["''\r\n]' -or (Test-Path -LiteralPath $Workspace)){throw 'NEW_RUNNER_TEMP_WORKSPACE_REQUIRED'}
$receipt=Get-Content -LiteralPath (Join-Path $Packages 'release-receipt.json') -Raw | ConvertFrom-Json
$zip=Join-Path $Packages $receipt.filename
if((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower() -ne $receipt.sha256){throw 'PACKAGE_HASH_MISMATCH'}
New-Item -ItemType Directory -Path $Workspace | Out-Null
$roots=[ordered]@{toolcache=$env:RUNNER_TOOL_CACHE;program_files=$env:ProgramFiles;program_files_x86=${env:ProgramFiles(x86)};chocolatey=(Join-Path $env:ProgramData 'chocolatey');msys='C:\msys64';strawberry='C:\Strawberry';tools='C:\tools';user_programs=(Join-Path $env:LOCALAPPDATA 'Programs');user_aliases=(Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps');user_uv=(Join-Path $env:APPDATA 'uv\python');user_scoop=(Join-Path $env:USERPROFILE 'scoop');user_pyenv=(Join-Path $env:USERPROFILE '.pyenv')}
foreach($dir in Get-ChildItem -LiteralPath 'C:\' -Directory){if($dir.Name -match '^(Python[0-9.-]*|Miniconda[0-9]*|Miniforge[0-9]*|Anaconda[0-9]*)$'){$roots['root_'+$dir.Name]=$dir.FullName}}
$resolved=@($roots.Values | Where-Object {$_ -and (Test-Path -LiteralPath $_ -PathType Container)} | ForEach-Object {[IO.Path]::GetFullPath($_).TrimEnd('\')} | Sort-Object -Unique)
if($resolved.Count -lt 3){throw 'RUNTIME_INSTALL_ROOTS_REQUIRED'}
$runtimeName='^(python[0-9.tw]*(?:_d)?|pypy[0-9.]*|pyw?|ipy|pip[0-9.]*)\.exe$'
function In-SelectedRoot([string]$name){foreach($root in $resolved){if($name.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){return $true}};return $false}
$script:scanIssues=0
function Find-Runtimes {
  $found=@{}
  foreach($root in $resolved){
    $issues=@()
    foreach($file in Get-ChildItem -LiteralPath $root -File -Recurse -Force -Filter '*.exe' -ErrorAction SilentlyContinue -ErrorVariable issues){if($file.Name -match $runtimeName){$found[$file.FullName]=$file}}
    $script:scanIssues+=@($issues).Count
  }
  return @($found.Values)
}
$before=@(Find-Runtimes)
if(!$before.Count){throw 'EXPECTED_PREINSTALLED_RUNTIME_INVENTORY_REQUIRED'}
foreach($command in Get-Command python,python3,py,pip -CommandType Application -All -ErrorAction SilentlyContinue){if(!(In-SelectedRoot ([IO.Path]::GetFullPath($command.Source)))){throw 'PYTHON_COMMAND_OUTSIDE_SELECTED_INSTALL_ROOTS'}}
$privateInventory=@()
foreach($file in $before){
  $target=[IO.Path]::GetFullPath($file.FullName)
  if(!(In-SelectedRoot $target) -or $file.Name -notmatch $runtimeName -or $file.PSIsContainer){throw 'EXACT_RUNTIME_EXECUTABLE_REQUIRED'}
  $pin=$null
  if(!($file.Attributes -band [IO.FileAttributes]::ReparsePoint)){$pin=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()}
  $privateInventory+=@{path=$target;sha256=$pin}
  # Only named interpreter/launcher executables on this disposable runner.
  # No recursive deletion, security policy changes or user-machine execution.
  Remove-Item -LiteralPath $target -Force
}
$privateInventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Workspace 'runtime-inventory-private.json') -Encoding UTF8
$remaining=@(Find-Runtimes)
$commands=@(Get-Command python,python3,py,pip -CommandType Application -All -ErrorAction SilentlyContinue)
if($remaining.Count -or $commands.Count -or $script:scanIssues){Write-Output ('ABSENCE_CHECK_COUNTS='+(@{remaining=$remaining.Count;commands=$commands.Count;scan_errors=$script:scanIssues}|ConvertTo-Json -Compress));throw 'PREEXISTING_PYTHON_ABSENCE_NOT_CONFIRMED'}
$registeredAvailable=0
foreach($root in @('HKLM:\SOFTWARE\Python','HKCU:\SOFTWARE\Python','HKLM:\SOFTWARE\WOW6432Node\Python')){
  if(Test-Path -LiteralPath $root){foreach($key in Get-ChildItem -LiteralPath $root -Recurse){if($key.PSChildName -eq 'InstallPath'){$location=$key.GetValue('');if($location -and (Test-Path -LiteralPath (Join-Path $location 'python.exe'))){$registeredAvailable++}}}}
}
if($registeredAvailable){throw 'REGISTERED_PYTHON_STILL_AVAILABLE'}
# Extract only after the pre-existing interpreter/launcher absence check.
$extract=Join-Path $Workspace 'extracted';Expand-Archive -LiteralPath $zip -DestinationPath $extract
$bundle=(Get-ChildItem -LiteralPath $extract -Directory).FullName
$harness=Join-Path $Workspace 'harness';New-Item -ItemType Directory -Path $harness | Out-Null
foreach($name in @('accept.py','build.py')){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $harness}
$inputs=Join-Path $Workspace 'packages';New-Item -ItemType Directory -Path $inputs | Out-Null
foreach($name in @($receipt.filename,'release-receipt.json')){Copy-Item -LiteralPath (Join-Path $Packages $name) -Destination $inputs}
$acceptance=Join-Path $Workspace 'fresh native acceptance'
$h=ConvertTo-Json -InputObject $harness -Compress;$p=ConvertTo-Json -InputObject $inputs -Compress;$a=ConvertTo-Json -InputObject $acceptance -Compress
# The bundled interpreter orchestrates checks. Actual CMD children start fresh
# with -I -B and must independently refuse every external import path.
$bootstrap="import sys;sys.path.insert(0,$h);from accept import accept;accept(__import__('pathlib').Path($p),__import__('pathlib').Path($a))"
& (Join-Path $bundle 'runtime\python.exe') -I -B -c $bootstrap
if($LASTEXITCODE -ne 0){throw 'NATIVE_WINDOWS_WITHOUT_PREINSTALLED_PYTHON_FAILED'}
$actual=Get-Content -LiteralPath (Join-Path $inputs 'acceptance.json') -Raw | ConvertFrom-Json
if($actual.status -ne 'PASS' -or $actual.cli_checks -ne 36 -or $actual.expected_review_outcomes -ne 17 -or $actual.browser){throw 'NATIVE_ACCEPTANCE_REQUIRED'}
$proof=@{schema=1;status='PASS';environment_kind='full-windows-host-preinstalled-python-executables-removed';environment_identifier=($env:ImageOS+':'+$env:ImageVersion);python_absent_before_extraction=$true;python_executables_removed=$before.Count;python_executables_remaining_before_extraction=0;registered_python_available=0;runtime_scan_errors=0;install_root_groups_scanned=$resolved.Count;native_windows_host=$true;runtime='3.14.10';bundled_runtime=$true;isolated=$true;original_storage_guard_passed=$true;command_checks=36;expected_review_outcomes=17;checks=$actual.checks;existing_run_refused_unchanged=$true;saved_run_reopened_without_writes=$true;tampered_run_refused_without_writes=$true;package_sha256=$receipt.sha256;packaging_revision=$receipt.packaging_revision;desktop_browser_tested_in_absence_job=$false;physical_operations_performed=$false;network_isolated=$false;raw_logs_published=$false;private_runs_published=$false;container_filesystem_qualification='UNSUPPORTED_VIRTUAL_NT_VOLUME_RETAINED_FAILURE'}
$proof | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Packages 'clean-acceptance.json') -Encoding UTF8
Write-Output ('PASS: full Windows native checks after removal of '+$before.Count+' pre-existing Python executables; no runtime executable or callable registered Python remained before bundle extraction.')
