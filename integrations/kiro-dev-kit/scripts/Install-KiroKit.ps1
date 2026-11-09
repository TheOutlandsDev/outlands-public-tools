param(
    [Parameter(Mandatory)][string]$Target,
    [string]$Python = 'python',
    [switch]$Apply,
    [switch]$Replace,
    [string]$AvailableModels,
    [string]$Primary,
    [string]$Review,
    [string]$Fast
)
$ErrorActionPreference = 'Stop'
$arguments = @('-B', (Join-Path $PSScriptRoot 'kiro_kit.py'), 'install', '--target', $Target)
if ($Apply) { $arguments += '--apply' }
if ($Replace) { $arguments += '--replace' }
if ($AvailableModels) { $arguments += @('--available-models', $AvailableModels) }
if ($Primary) { $arguments += @('--primary', $Primary) }
if ($Review) { $arguments += @('--review', $Review) }
if ($Fast) { $arguments += @('--fast', $Fast) }
& $Python @arguments
if ($LASTEXITCODE -ne 0) { throw "Kiro kit installation failed with exit $LASTEXITCODE" }
