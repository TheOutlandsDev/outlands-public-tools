param(
    [Parameter(Mandatory)][string]$Target,
    [Parameter(Mandatory)][string]$Receipt,
    [string]$Python = 'python',
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$arguments = @('-B', (Join-Path $PSScriptRoot 'kiro_kit.py'), 'restore', '--target', $Target, '--receipt', $Receipt)
if ($Apply) { $arguments += '--apply' }
& $Python @arguments
if ($LASTEXITCODE -ne 0) { throw "Kiro kit restore failed with exit $LASTEXITCODE" }
