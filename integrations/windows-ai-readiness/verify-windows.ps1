param(
    [string]$Python = 'python',
    [string]$Node = 'node',
    [string]$Java = 'java',
    [string]$Maven = 'mvn',
    [string]$Aws = 'aws',
    [string]$KiroCli = 'kiro-cli'
)

$ErrorActionPreference = 'Stop'

function Test-Version {
    param([string]$Name, [string]$Executable, [string[]]$Arguments)
    try {
        $command = Get-Command -Name $Executable -ErrorAction Stop
        $output = (& $command.Source @Arguments 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        [pscustomobject]@{ name = $Name; status = 'PASS'; version = ($output -split "`r?`n")[0] }
    } catch {
        [pscustomobject]@{ name = $Name; status = 'FAIL'; detail = $_.Exception.Message }
    }
}

$results = @(
    Test-Version 'Python' $Python @('--version')
    Test-Version 'pip' $Python @('-m', 'pip', '--version')
    Test-Version 'Node.js' $Node @('--version')
    Test-Version 'Java' $Java @('-version')
    Test-Version 'Maven' $Maven @('--version')
    Test-Version 'AWS CLI' $Aws @('--version')
    Test-Version 'Kiro CLI' $KiroCli @('--version')
)

$report = [pscustomobject]@{
    format = 'outlands-windows-ai-readiness-v1'
    offline = $true
    results = $results
}
$report | ConvertTo-Json -Depth 5
if (@($results | Where-Object status -eq 'FAIL').Count -gt 0) { exit 1 }
