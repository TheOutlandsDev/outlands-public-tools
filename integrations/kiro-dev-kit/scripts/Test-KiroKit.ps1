param(
    [Parameter(Mandatory)][string]$Target,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
& $Python -B (Join-Path $PSScriptRoot 'kiro_kit.py') verify --target $Target
if ($LASTEXITCODE -ne 0) { throw "Kiro kit verification failed with exit $LASTEXITCODE" }
