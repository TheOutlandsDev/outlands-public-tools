# First stage only: verify package files and inspect metadata. Never installs.
[CmdletBinding()]
param(
    [string]$Repository,
    [ValidateRange(0,4)][int]$MaxDepth=2,
    [ValidateRange(1,2000)][int]$MaxEntries=500,
    [switch]$IncludeRelativePaths
)
$ErrorActionPreference='Stop'
$integrity='NOT_VERIFIED'; $checked=0; $laptop=$null; $project=$null; $issues=@()
try {
    if ([string]$ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { throw 'LIMITED_LANGUAGE_MODE' }
    $manifestPath=Join-Path $PSScriptRoot 'PACKAGE-MANIFEST.json'
    $manifestFile=Get-Item -LiteralPath $manifestPath -Force
    if (($manifestFile.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $manifestFile.Length -gt 131072) { throw 'INVALID_MANIFEST' }
    $manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.version -ne '1.2.0' -or $manifest.files.Count -lt 10) { throw 'INVALID_MANIFEST' }
    $required=@('START-HERE.ps1','scripts/Inspect-KiroLaptop.ps1','scripts/Inspect-Repository.ps1','scripts/Install-KiroKit.ps1','scripts/kiro_kit.py','versions.json')
    $seen=@{}
    foreach($entry in $manifest.files) {
        $name=[string]$entry.path
        if ($name -notmatch '^[A-Za-z0-9_./-]+$' -or $name.StartsWith('/') -or $name.Contains('//') -or @($name.Split('/') | Where-Object { $_ -in @('.','..') }).Count -or $seen.ContainsKey($name)) { throw 'UNSAFE_MANIFEST_ENTRY' }
        if ($entry.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'INVALID_DIGEST' }
        $seen[$name]=$true
        $path=Join-Path $PSScriptRoot $name
        $item=Get-Item -LiteralPath $path -Force
        if ($item.PSIsContainer -or $item.Length -gt 1048576) { throw 'INVALID_PACKAGE_FILE' }
        $part=$item
        while($null -ne $part) {
            if (($part.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'LINKED_PACKAGE_FILE' }
            if ($part -is [IO.FileInfo]) { $part=$part.Directory } else { $part=$part.Parent }
        }
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'PACKAGE_DIGEST_MISMATCH' }
        $checked++
    }
    foreach($name in $required) { if (-not $seen.ContainsKey($name)) { throw 'REQUIRED_FILE_NOT_LISTED' } }
    $integrity='MATCHES_DECLARED_HASHES'
    $laptop=& (Join-Path $PSScriptRoot 'scripts/Inspect-KiroLaptop.ps1') | ConvertFrom-Json
    if ($Repository) {
        $parameters=@{ Repository=$Repository; MaxDepth=$MaxDepth; MaxEntries=$MaxEntries; IncludeRelativePaths=$IncludeRelativePaths }
        $project=& (Join-Path $PSScriptRoot 'scripts/Inspect-Repository.ps1') @parameters | ConvertFrom-Json
    }
} catch { $issues += 'PACKAGE_OR_PROBE_NOT_VERIFIED_REVIEW_LOCAL_POLICY_AND_SOURCE' }

$pythonMetadata=$false
if ($null -ne $laptop) {
    $pythonMetadata=(@($laptop.tools | Where-Object { $_.tool -eq 'python' -and -not $_.windows_python_alias -and $_.file_version_metadata -match '^3\.15(?:\.|$)' }).Count -gt 0)
}

[pscustomobject]@{
    format='kiro-preinstall-probe-v1'; kit_version='1.2.0'; stage='READ_ONLY_BEFORE_INSTALL'
    package_integrity=$integrity; listed_files_checked=$checked; issues=@($issues)
    laptop=$laptop; repository=$project
    prerequisites=[pscustomobject]@{
        python315_on_path_metadata=$pythonMetadata
        runtime_functionality='NOT_TESTED'
        no_admin_required_for_probe=$true
    }
    installer_started=$false; runtimes_started=$false; settings_changed=$false
    installation_permission='NOT_DETERMINED'; model_and_bedrock_access='NOT_VERIFIED'
    next_step='REVIEW_OUTPUT_AND_UNKNOWNS_BEFORE_ANY_EXPLICIT_INSTALL_ACTION'
    limits='Listed-file consistency only, not a publisher signature or an exhaustive device policy test. No installer, runtime, project command, sign-in, or service request is performed.'
} | ConvertTo-Json -Depth 16
