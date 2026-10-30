param([Parameter(Mandatory=$true)][string]$Packages,[Parameter(Mandatory=$true)][string]$Workspace)
$ErrorActionPreference='Stop'
$image='mcr.microsoft.com/windows/servercore@sha256:12eb9fb0087ea6c512db739291992948caa98f6fbef9e85ec4749ad4df3f0735'
$digest='sha256:12eb9fb0087ea6c512db739291992948caa98f6fbef9e85ec4749ad4df3f0735'
if(Test-Path -LiteralPath $Workspace){throw 'NEW_CLEAN_WORKSPACE_REQUIRED'}
$receipt=Get-Content -LiteralPath (Join-Path $Packages 'release-receipt.json') -Raw | ConvertFrom-Json
$zip=Join-Path $Packages $receipt.filename
if((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower() -ne $receipt.sha256){throw 'PACKAGE_HASH_MISMATCH'}
New-Item -ItemType Directory -Path $Workspace | Out-Null
$extract=Join-Path $Workspace 'extracted'; Expand-Archive -LiteralPath $zip -DestinationPath $extract
$bundle=(Get-ChildItem -LiteralPath $extract -Directory).FullName
$harness=Join-Path $Workspace 'harness';New-Item -ItemType Directory -Path $harness | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'clean_probe.ps1') -Destination $harness
$results=Join-Path $Workspace 'results';New-Item -ItemType Directory -Path $results | Out-Null
$privateVolume=Join-Path $Workspace 'private-ntfs-volume';New-Item -ItemType Directory -Path $privateVolume | Out-Null
$dockerService=Get-Service -Name docker
if($dockerService.Status -ne 'Running'){Start-Service -Name docker; (Get-Service -Name docker).WaitForStatus('Running',[TimeSpan]::FromSeconds(90))}
docker version
if($LASTEXITCODE -ne 0){throw 'WINDOWS_CONTAINER_DAEMON_REQUIRED'}
docker pull $image
if($LASTEXITCODE -ne 0){throw 'PINNED_WINDOWS_IMAGE_PULL_FAILED'}
docker run --rm --isolation=process --network none --mount "type=bind,source=$harness,target=C:\harness,readonly" --mount "type=bind,source=$results,target=C:\results" $image powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\harness\clean_probe.ps1 -Mode preflight -ImageDigest $digest
if($LASTEXITCODE -ne 0){throw 'PYTHON_FREE_BASE_PREFLIGHT_FAILED'}
docker run --rm --isolation=process --network none --mount "type=bind,source=$bundle,target=C:\bundle,readonly" --mount "type=bind,source=$harness,target=C:\harness,readonly" --mount "type=bind,source=$results,target=C:\results" --mount "type=bind,source=$privateVolume,target=R:\" $image powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\harness\clean_probe.ps1 -Mode run -ImageDigest $digest
if($LASTEXITCODE -ne 0){throw 'PYTHON_FREE_WINDOWS_ACCEPTANCE_FAILED'}
$proof=Get-Content -LiteralPath (Join-Path $results 'clean-acceptance.json') -Raw | ConvertFrom-Json
if($proof.status -ne 'PASS' -or !$proof.python_absent_in_pristine_base){throw 'CLEAN_PROOF_REQUIRED'}
$proof | Add-Member -NotePropertyName package_sha256 -NotePropertyValue $receipt.sha256
$proof | Add-Member -NotePropertyName packaging_revision -NotePropertyValue $receipt.packaging_revision
$proof | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Packages 'clean-acceptance.json') -Encoding UTF8
