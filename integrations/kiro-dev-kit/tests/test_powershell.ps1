param([Parameter(Mandatory)][string]$Python)
$ErrorActionPreference = 'Stop'
$scripts = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts'
$taskRoot = Join-Path ([IO.Path]::GetTempPath()) ('kiro-kit-wrappers-' + [guid]::NewGuid().ToString('N'))
$project = Join-Path $taskRoot 'project with spaces'
New-Item -ItemType Directory -Path $project -Force | Out-Null
$preview = (& (Join-Path $scripts 'Install-KiroKit.ps1') -Target $project -Python $Python | Out-String) | ConvertFrom-Json
if ($preview.action -ne 'preview' -or (Get-ChildItem -LiteralPath $project -Force).Count) { throw 'Preview wrote project files' }
$installed = (& (Join-Path $scripts 'Install-KiroKit.ps1') -Target $project -Python $Python -Apply | Out-String) | ConvertFrom-Json
$report = (& (Join-Path $scripts 'Test-KiroKit.ps1') -Target $project -Python $Python | Out-String) | ConvertFrom-Json
if (-not $report.configuration_files_present -or $report.ready_for_managed_work) { throw 'Unexpected qualification state' }
$restored = (& (Join-Path $scripts 'Restore-KiroKit.ps1') -Target $project -Receipt $installed.receipt -Python $Python -Apply | Out-String) | ConvertFrom-Json
if ($restored.action -ne 'restored' -or (Test-Path -LiteralPath (Join-Path $project 'AGENTS.md'))) { throw 'Restore failed' }
Write-Host 'PASS: PowerShell preview/install/verify/restore with paths containing spaces.'
# Disposable evidence remains in the OS temp directory; no recursive cleanup.
