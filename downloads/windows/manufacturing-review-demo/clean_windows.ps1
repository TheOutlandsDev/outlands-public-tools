param([Parameter(Mandatory=$true)][string]$Packages,[Parameter(Mandatory=$true)][string]$Workspace)
$ErrorActionPreference='Stop'
if($env:GITHUB_ACTIONS -ne 'true' -or $env:GITHUB_REPOSITORY -ne 'TheOutlandsDev/outlands-public-tools' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted'){throw 'EPHEMERAL_GITHUB_RUNNER_REQUIRED'}
$Workspace=[IO.Path]::GetFullPath($Workspace)
$tempRoot=[IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\')+'\'
if(!$Workspace.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'RUNNER_TEMP_WORKSPACE_REQUIRED'}
if(Get-Volume -DriveLetter R -ErrorAction SilentlyContinue){throw 'SCRATCH_DRIVE_MUST_NOT_EXIST'}
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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'storage_probe.py') -Destination $harness
$results=Join-Path $Workspace 'results';New-Item -ItemType Directory -Path $results | Out-Null
# Create only a new tiny virtual disk in this fresh ephemeral CI workspace.
# Initialize/format only the RAW disk associated with that exact new image.
$vhd=Join-Path $Workspace 'fresh-scratch.vhdx'
if((Test-Path -LiteralPath $vhd) -or $vhd -match '["\r\n]'){throw 'NEW_SCRATCH_IMAGE_REQUIRED'}
$diskScript=Join-Path $Workspace 'create-scratch.txt'
@('create vdisk file="'+$vhd+'" maximum=128 type=expandable','exit') | Set-Content -LiteralPath $diskScript -Encoding ASCII
diskpart.exe /s $diskScript | Out-Null
if($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $vhd)){throw 'SCRATCH_IMAGE_CREATION_FAILED'}
$mounted=$null
try {
  $mounted=Mount-DiskImage -ImagePath $vhd -Access ReadWrite -NoDriveLetter -PassThru
  if([IO.Path]::GetFullPath($mounted.ImagePath) -ne $vhd -or !$mounted.Attached){throw 'EXACT_NEW_IMAGE_REQUIRED'}
  $newDisks=@(Get-DiskImage -ImagePath $vhd | Get-Disk)
  if($newDisks.Count -ne 1 -or $newDisks[0].PartitionStyle -ne 'RAW' -or $newDisks[0].Size -ne 128MB -or $newDisks[0].IsBoot -or $newDisks[0].IsSystem){throw 'EXACT_NEW_RAW_SCRATCH_DISK_REQUIRED'}
  $newDisks[0] | Initialize-Disk -PartitionStyle GPT -PassThru | New-Partition -DriveLetter R -UseMaximumSize | Format-Volume -FileSystem NTFS -NewFileSystemLabel 'MRD-QUALIFY' -Confirm:$false | Out-Null
  $scratch=Get-Volume -DriveLetter R
  if($scratch.FileSystem -ne 'NTFS' -or (Get-Partition -DriveLetter R | Get-Disk).Number -ne $newDisks[0].Number){throw 'SCRATCH_VOLUME_MISMATCH'}
$dockerService=Get-Service -Name docker
if($dockerService.Status -ne 'Running'){Start-Service -Name docker; (Get-Service -Name docker).WaitForStatus('Running',[TimeSpan]::FromSeconds(90))}
docker version
if($LASTEXITCODE -ne 0){throw 'WINDOWS_CONTAINER_DAEMON_REQUIRED'}
docker pull $image
if($LASTEXITCODE -ne 0){throw 'PINNED_WINDOWS_IMAGE_PULL_FAILED'}
docker run --rm --isolation=process --network none --mount "type=bind,source=$harness,target=C:\harness,readonly" --mount "type=bind,source=$results,target=C:\results" $image powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\harness\clean_probe.ps1 -Mode preflight -ImageDigest $digest
if($LASTEXITCODE -ne 0){throw 'PYTHON_FREE_BASE_PREFLIGHT_FAILED'}
$privateMount='R:\:R:'
docker run --rm --isolation=process --network none --mount "type=bind,source=$bundle,target=C:\bundle,readonly" --mount "type=bind,source=$harness,target=C:\harness,readonly" --mount "type=bind,source=$results,target=C:\results" --volume $privateMount $image powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\harness\clean_probe.ps1 -Mode run -ImageDigest $digest
if($LASTEXITCODE -ne 0){throw 'PYTHON_FREE_WINDOWS_ACCEPTANCE_FAILED'}
$proof=Get-Content -LiteralPath (Join-Path $results 'clean-acceptance.json') -Raw | ConvertFrom-Json
if($proof.status -ne 'PASS' -or !$proof.python_absent_in_pristine_base){throw 'CLEAN_PROOF_REQUIRED'}
$proof | Add-Member -NotePropertyName package_sha256 -NotePropertyValue $receipt.sha256
$proof | Add-Member -NotePropertyName packaging_revision -NotePropertyValue $receipt.packaging_revision
$proof | Add-Member -NotePropertyName fresh_ntfs_scratch_disk -NotePropertyValue $true
$proof | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Packages 'clean-acceptance.json') -Encoding UTF8
} finally {
  if($mounted -and (Get-DiskImage -ImagePath $vhd).Attached){Dismount-DiskImage -ImagePath $vhd}
}
