# Read-only metadata inspection. Does not start discovered applications,
# invoke an installer, request elevation, inspect credentials, or write files.
[CmdletBinding()]
param()

$os = $null
try {
    $info = Get-CimInstance -ClassName Win32_OperatingSystem -Property Caption,Version,OSArchitecture -ErrorAction Stop
    $os = [pscustomobject]@{ status='READ'; caption=$info.Caption; version=$info.Version; architecture=$info.OSArchitecture }
} catch { $os = [pscustomobject]@{ status='UNKNOWN_OR_NOT_READABLE' } }

$tools = foreach ($name in @('kiro','kiro-cli','python','py','node','java','javac','mvn','git','aws')) {
    $found = @(Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue)
    $aliasFound = $false
    $fileVersion = $null
    foreach ($command in $found) {
        if ($command.Source -match '\\Microsoft\\WindowsApps\\python[^\\]*\.exe$') { $aliasFound = $true }
        elseif (-not $fileVersion) {
            try {
                $file = Get-Item -LiteralPath $command.Source -ErrorAction Stop
                $value = [string]$file.VersionInfo.ProductVersion
                if ($value -match '^\d+(?:\.\d+){1,5}$') { $fileVersion = $value }
            } catch { }
        }
    }
    [pscustomobject]@{ tool=$name; found_on_path=($found.Count -gt 0); windows_python_alias=$aliasFound; file_version_metadata=$fileVersion; runtime_execution='NOT_PERFORMED' }
}

$knownKiro = @(
    "$env:LOCALAPPDATA\Programs\Kiro\Kiro.exe",
    "$env:ProgramFiles\Kiro\Kiro.exe",
    "$env:LOCALAPPDATA\Kiro-Cli\kiro-cli.exe"
)
$knownKiroFound = $false
foreach ($candidate in $knownKiro) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf -ErrorAction SilentlyContinue) { $knownKiroFound = $true }
}

$execution = @()
try {
    $execution = @(Get-ExecutionPolicy -List -ErrorAction Stop | Select-Object Scope,ExecutionPolicy)
} catch { $execution = @([pscustomobject]@{ status='UNKNOWN_OR_NOT_READABLE' }) }

$installerPolicy = foreach ($scope in @('HKLM')) {
    try {
        $policy = Get-ItemProperty -LiteralPath "${scope}:\Software\Policies\Microsoft\Windows\Installer" -Name DisableMSI -ErrorAction Stop
        [pscustomobject]@{ scope=$scope; status='READ'; disable_msi=$policy.DisableMSI }
    } catch { [pscustomobject]@{ scope=$scope; status='NOT_SET_OR_NOT_READABLE'; disable_msi=$null } }
}

[pscustomobject]@{
    format='kiro-laptop-inspection-v1'
    read_only=$true
    applications_started=0
    installation_allowed='NOT_DETERMINED'
    application_control_policy='NOT_EVALUATED'
    os=$os
    powershell_language_mode=[string]$ExecutionContext.SessionState.LanguageMode
    execution_policy=$execution
    tools=@($tools)
    kiro_found_in_known_locations=$knownKiroFound
    installer_policy=@($installerPolicy)
    note='PATH presence is not installation proof. Execution policy is not installer permission. MSI policy does not establish whether a Kiro EXE or company deployment is allowed.'
} | ConvertTo-Json -Depth 6
