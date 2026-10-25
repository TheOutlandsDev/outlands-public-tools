#requires -Version 7.2
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$moduleRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not [IO.Path]::IsPathFullyQualified($Destination) -or [IO.Path]::GetFullPath($Destination) -cne $Destination -or $Destination.StartsWith('\\') -or $Destination.StartsWith('//') -or $Destination.StartsWith($moduleRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.File]::Exists($Destination) -or [IO.Directory]::Exists($Destination)) { throw 'Destination must be a new absolute local directory outside the source module.' }
[void](New-Item -ItemType Directory -Path $Destination -ErrorAction Stop)
$stream=[IO.File]::Open((Join-Path $Destination 'package.zip'),[IO.FileMode]::CreateNew)
$zip=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create,$false)
try {
    foreach ($pair in @(@('README.txt',"Example Orchard utility package.`n"),@('settings/example.ini',"[demo]`nmode=preview`n"))) {
        $entry=$zip.CreateEntry($pair[0]); $output=$entry.Open()
        try { $bytes=[Text.Encoding]::UTF8.GetBytes($pair[1]); $output.Write($bytes,0,$bytes.Length) } finally { $output.Dispose() }
    }
} finally { $zip.Dispose(); $stream.Dispose() }
$policy=@{schemaVersion=1;requiredMembers=@('README.txt','settings/example.ini');allowedMembers=@('README.txt','settings/example.ini');forbiddenMembers=@('private.env');textRules=@(@{member='settings/example.ini';containsAll=@('[demo]','mode=preview');containsNone=@('mode=production')})}
$policyStream=[IO.File]::Open((Join-Path $Destination 'policy.json'),[IO.FileMode]::CreateNew)
try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($policy|ConvertTo-Json -Depth 8)+"`n"); $policyStream.Write($bytes,0,$bytes.Length) } finally { $policyStream.Dispose() }
Write-Output 'Created fictional package.zip and policy.json. No real package or device is involved.'
