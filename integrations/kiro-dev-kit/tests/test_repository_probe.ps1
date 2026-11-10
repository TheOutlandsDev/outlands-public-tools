$ErrorActionPreference='Stop'
$kit=Split-Path -Parent $PSScriptRoot
$inspector=Join-Path $kit 'scripts/Inspect-Repository.ps1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('kiro-repo-fixture-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
function Write-Fixture([string]$Name,[string]$Text) {
    $path=Join-Path $root $Name
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)) | Out-Null
    [IO.File]::WriteAllText($path,$Text,[Text.UTF8Encoding]::new($false))
}
function Require($Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
Write-Fixture 'pyproject.toml' @'
[project]
requires-python = ">=3.12,<3.14"
[tool.pytest.ini_options]
testpaths = ["tests"]
'@
Write-Fixture 'service/package.json' '{"engines":{"node":">=20 <27"},"packageManager":"pnpm@10.0.0","scripts":{"test":"write private-command-sentinel","build":"do-not-run"}}'
Write-Fixture 'service/pnpm-lock.yaml' '# Only filename presence is used'
Write-Fixture 'conflict/package.json' '{"scripts":{"test":"do-not-run"}}'
Write-Fixture 'conflict/package-lock.json' '{}'
Write-Fixture 'conflict/yarn.lock' '# mixed lockfiles'
Write-Fixture 'java/pom.xml' '<project xmlns="http://maven.apache.org/POM/4.0.0"><properties><maven.compiler.release>17</maven.compiler.release></properties></project>'
Write-Fixture 'java/mvnw.cmd' 'echo do-not-run'
Write-Fixture 'dynamic/build.gradle.kts' 'java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }'
Write-Fixture 'dynamic/gradlew.bat' 'echo do-not-run'
Write-Fixture 'unknown/setup.cfg' "[options]`npython_requires = ~=3.12`n"
Write-Fixture 'permitted/pyproject.toml' "[project]`nrequires-python = '>=3.12,==3.15.*'`n"
Write-Fixture 'excluded/setup.cfg' "[options]`npython_requires = !=3.15.*`n"
Write-Fixture 'oversized/package.json' (' ' * 262145)
Write-Fixture 'broken/package.json' '{not json'
Write-Fixture 'xml/pom.xml' '<!DOCTYPE project [<!ENTITY x SYSTEM "file:///private-entity-sentinel">]><project>&x;</project>'
Write-Fixture 'node_modules/hidden/package.json' '{"engines":{"node":"0"}}'
Write-Fixture '.aws/pyproject.toml' '[project]'
Write-Fixture '.env' 'private-credential-sentinel'
$before=@(Get-ChildItem -LiteralPath $root -Recurse -File -Force | ForEach-Object { $_.FullName+':'+(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash })
$text=(& $inspector -Repository $root | Out-String)
$result=$text | ConvertFrom-Json
Require ($result.commands_executed -eq 0 -and $result.read_only) 'Probe executed a project command'
Require ($text -notmatch 'private-command-sentinel|private-credential-sentinel|private-entity-sentinel') 'Private content escaped the report'
Require ($text -notmatch [regex]::Escape($root)) 'Absolute root escaped the report'
$python=@($result.records | Where-Object { $_.manifest -eq 'pyproject.toml' })
Require ($python.Count -eq 2) 'Excluded directory was inspected'
Require (@($python | Where-Object { $_.details.constraints[0].python315 -eq 'EXCLUDED_BY_DECLARATION' }).Count -eq 1) 'Python 3.15 exclusion was not detected'
Require (@($python | Where-Object { $_.details.constraints[0].python315 -eq 'PERMITTED_BY_DECLARATION_ONLY' }).Count -eq 1) 'Python wildcard declaration was not interpreted'
$node=@($result.records | Where-Object { $_.details.language -eq 'node' -and $_.details.package_manager -eq 'pnpm' })
Require ($node.Count -eq 1 -and $node[0].details.candidates[0].command -eq 'pnpm run test') 'Node command discovery failed'
$mixed=@($result.records | Where-Object { $_.details.conflicting_package_managers })
Require ($mixed.Count -eq 1 -and $mixed[0].details.candidates.Count -eq 0) 'Conflicting locks were guessed'
$maven=@($result.records | Where-Object { $_.details.build_system -eq 'maven' })
Require ($maven.Count -eq 1 -and $maven[0].details.declared_versions[0].value -eq '17') 'Maven declaration was not read'
$gradle=@($result.records | Where-Object { $_.details.build_system -eq 'gradle' })
Require ($gradle[0].details.literal_toolchain_hints[0] -eq '21') 'Gradle literal hint was not read'
$unknown=@($result.records | Where-Object { $_.manifest -eq 'setup.cfg' })
Require (@($unknown | Where-Object { $_.details.constraints[0].python315 -eq 'UNKNOWN' }).Count -eq 1) 'Unsupported version grammar was treated as compatible'
Require (@($unknown | Where-Object { $_.details.constraints[0].python315 -eq 'EXCLUDED_BY_DECLARATION' }).Count -eq 1) 'Negated Python wildcard was not interpreted'
Require (@($result.records | Where-Object status -eq 'UNREADABLE_OVERSIZED_OR_UNSUPPORTED').Count -eq 3) 'Malformed, oversized, or DTD manifest was accepted'
$shallow=(& $inspector -Repository $root -MaxDepth 0 | Out-String) | ConvertFrom-Json
Require ($shallow.scan_incomplete -and $shallow.records.Count -eq 1) 'Depth bound was not reported'
$bounded=(& $inspector -Repository $root -MaxEntries 1 | Out-String) | ConvertFrom-Json
Require ($bounded.entries_examined -eq 1 -and $bounded.scan_incomplete) 'Entry bound was not enforced'
$withPaths=(& $inspector -Repository $root -IncludeRelativePaths | Out-String) | ConvertFrom-Json
Require ($withPaths.relative_paths_included -and @($withPaths.records | Where-Object relative_path -eq 'service/package.json').Count -eq 1) 'Explicit relative evidence paths failed'
$after=@(Get-ChildItem -LiteralPath $root -Recurse -File -Force | ForEach-Object { $_.FullName+':'+(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash })
Require (@(Compare-Object $before $after).Count -eq 0) 'Inspection modified the fixture'
Write-Host 'PASS: static repository discovery, exclusions, bounds, safe parsing, privacy, and unchanged fixture bytes.'

# The package entry point must not proceed after a changed listed script.
$entry=& (Join-Path $kit 'START-HERE.ps1') -Repository $root | Out-String | ConvertFrom-Json
Require ($entry.package_integrity -eq 'MATCHES_DECLARED_HASHES' -and -not $entry.installer_started -and -not $entry.runtimes_started) 'First-stage probe did not remain read-only'
$copy=Join-Path ([IO.Path]::GetTempPath()) ('kiro-package-fixture-'+[guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $kit -Destination $copy -Recurse
[IO.File]::AppendAllText((Join-Path $copy 'scripts/Inspect-KiroLaptop.ps1'),"`n# changed fixture`n")
$changed=& (Join-Path $copy 'START-HERE.ps1') | Out-String | ConvertFrom-Json
Require ($changed.package_integrity -ne 'MATCHES_DECLARED_HASHES' -and $null -eq $changed.laptop) 'Changed package code was executed'
Write-Host 'PASS: package hash mismatch blocks child probes and no installation is started.'

# Give the copy a self-consistent modified installer that fails if invoked.
# The first-stage entry point must not execute it, even though it is listed.
$copy2=Join-Path ([IO.Path]::GetTempPath()) ('kiro-no-install-fixture-'+[guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $kit -Destination $copy2 -Recurse
$marker=Join-Path $copy2 'installer-was-started'
$installer=Join-Path $copy2 'scripts/Install-KiroKit.ps1'
$poison='[IO.File]::WriteAllText('''+$marker.Replace("'","''")+''',''unexpected''); throw ''INSTALLER_STARTED'''
[IO.File]::WriteAllText($installer,$poison,[Text.UTF8Encoding]::new($false))
$inventory=Get-Content -LiteralPath (Join-Path $copy2 'PACKAGE-MANIFEST.json') -Raw | ConvertFrom-Json
foreach($entry in $inventory.files) { if($entry.path -eq 'scripts/Install-KiroKit.ps1') { $entry.sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant() } }
[IO.File]::WriteAllText((Join-Path $copy2 'PACKAGE-MANIFEST.json'),($inventory|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$readOnly=& (Join-Path $copy2 'START-HERE.ps1') | Out-String | ConvertFrom-Json
Require ($readOnly.package_integrity -eq 'MATCHES_DECLARED_HASHES' -and -not (Test-Path -LiteralPath $marker)) 'First probe invoked an installer'
Write-Host 'PASS: an available installer is not invoked by the first-stage entry point.'

# Manifest names use forward slashes only, including on Windows.
foreach($unsafe in @('../outside.ps1','..\outside.ps1','/outside.ps1')) {
    $inventory.files[0].path=$unsafe
    [IO.File]::WriteAllText((Join-Path $copy2 'PACKAGE-MANIFEST.json'),($inventory|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
    $blocked=& (Join-Path $copy2 'START-HERE.ps1') | Out-String | ConvertFrom-Json
    Require ($blocked.package_integrity -ne 'MATCHES_DECLARED_HASHES' -and $null -eq $blocked.laptop) 'Unsafe manifest path was accepted'
}
Write-Host 'PASS: unsafe manifest paths are refused before any child probe.'
