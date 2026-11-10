# Bounded static manifest inspection; no project command or runtime is invoked.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Repository,
    [ValidateRange(0,4)][int]$MaxDepth = 2,
    [ValidateRange(1,2000)][int]$MaxEntries = 500,
    [switch]$IncludeRelativePaths
)
$ErrorActionPreference = 'Stop'

function Test-LinkedPath([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $true }
        $item = $item.Parent
    }
    return $false
}

function Get-SafeText([IO.FileInfo]$File) {
    if ($File.Length -gt 262144) { throw 'MANIFEST_SIZE_LIMIT' }
    if (($File.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'LINK_SKIPPED' }
    $stream = [IO.File]::Open($File.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if ($stream.Length -gt 262144) { throw 'MANIFEST_SIZE_LIMIT' }
        $reader = [IO.StreamReader]::new($stream,[Text.UTF8Encoding]::new($false,$true),$true)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $stream.Dispose() }
}

function Get-RangeValue($Value) {
    if ($Value -is [string] -and $Value.Length -le 128 -and $Value -match '^[0-9vVxX*.,<>=!~^| +\-]+$' -and $Value -match '\d') { return $Value.Trim() }
    return $null
}

function Get-Python315Status([string]$Constraint) {
    if (-not $Constraint) { return 'UNKNOWN' }
    $target = [version]'3.15.2'
    $unknown = $false
    foreach ($part in $Constraint.Split(',')) {
        if ($part.Trim() -notmatch '^(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,2})(\.\*)?$') { $unknown=$true; continue }
        $op=$Matches[1]; $text=$Matches[2]; $wildcard=[bool]$Matches[3]
        if ($wildcard) {
            if ($op -notin @('==','!=')) { $unknown=$true; continue }
            $equal=('3.15.2' -eq $text -or '3.15.2'.StartsWith($text+'.'))
            if (($op -eq '==' -and -not $equal) -or ($op -eq '!=' -and $equal)) { return 'EXCLUDED_BY_DECLARATION' }
            continue
        }
        $numbers=@($text.Split('.'))
        while ($numbers.Count -lt 3) { $numbers += '0' }
        try { $bound=[version]($numbers -join '.') } catch { $unknown=$true; continue }
        $comparison=$target.CompareTo($bound)
        $passed=switch($op) {
            '>=' { $comparison -ge 0 }; '<=' { $comparison -le 0 }
            '>' { $comparison -gt 0 }; '<' { $comparison -lt 0 }
            '==' { $comparison -eq 0 }; '!=' { $comparison -ne 0 }
        }
        if (-not $passed) { return 'EXCLUDED_BY_DECLARATION' }
    }
    if ($unknown) { return 'UNKNOWN' }
    return 'PERMITTED_BY_DECLARATION_ONLY'
}

function New-Candidate([string]$Command,[string]$Evidence) {
    [pscustomobject]@{ command=$Command; evidence=$Evidence; state='PROPOSED_NOT_EXECUTED'; review_required=$true }
}

function Get-Field($Object,[string]$Name) {
    if ($null -eq $Object) { return $null }
    $property=$Object.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}

function Read-PythonManifest([string]$Text,[string]$Name) {
    $section=''; $constraints=@(); $candidates=@()
    foreach ($line in ($Text -split '\r?\n')) {
        if ($line -match '^\s*\[([^\]]+)\]\s*(?:#.*)?$') { $section=$Matches[1]; continue }
        if (($Name -eq 'pyproject.toml' -and $section -eq 'project' -and $line -match '^\s*requires-python\s*=\s*["'']([^"'']+)["'']\s*(?:#.*)?$') -or
            ($Name -eq 'setup.cfg' -and $section -eq 'options' -and $line -match '^\s*python_requires\s*=\s*([^#;]+)')) {
            $value=Get-RangeValue $Matches[1]
            if ($value) { $constraints += [pscustomobject]@{ value=$value; python315=Get-Python315Status $value } }
        }
    }
    if ($Text -match '(?m)^\s*\[(tool\.pytest\.ini_options|tool:pytest)\]') { $candidates += New-Candidate 'python -m pytest' 'pytest configuration section' }
    if ($Text -match '(?m)^\s*\[tool\.ruff(?:\.[^\]]+)?\]') { $candidates += New-Candidate 'python -m ruff check .' 'tool.ruff section' }
    if ($Text -match '(?m)^\s*\[tool\.mypy\]') { $candidates += New-Candidate 'python -m mypy .' 'tool.mypy section' }
    [pscustomobject]@{ language='python'; interpretation='BOUNDED_LITERAL_HINTS_NOT_FULL_TOML_OR_INI'; constraints=@($constraints); candidates=@($candidates); dependency_compatibility='NOT_TESTED' }
}

function Read-NodeManifest([string]$Text,[string[]]$Names) {
    $data=$Text | ConvertFrom-Json -ErrorAction Stop
    if ($data -isnot [pscustomobject]) { throw 'NODE_MANIFEST_OBJECT_REQUIRED' }
    $engine=Get-RangeValue (Get-Field (Get-Field $data 'engines') 'node')
    $packageManager=Get-Field $data 'packageManager'
    $scripts=Get-Field $data 'scripts'
    $manager=$null; $managerVersion=$null
    if ($packageManager -is [string] -and $packageManager -match '^(npm|pnpm|yarn|bun)@(\d+(?:\.\d+){1,2})(?:\+sha(?:224|256|384|512)\.[a-fA-F0-9]+)?$') {
        $manager=$Matches[1]; $managerVersion=$Matches[2]
    }
    $locks=@()
    if ('package-lock.json' -in $Names -or 'npm-shrinkwrap.json' -in $Names) { $locks += 'npm' }
    if ('pnpm-lock.yaml' -in $Names) { $locks += 'pnpm' }
    if ('yarn.lock' -in $Names) { $locks += 'yarn' }
    if ('bun.lock' -in $Names -or 'bun.lockb' -in $Names) { $locks += 'bun' }
    if (-not $manager -and $locks.Count -eq 1) { $manager=$locks[0] }
    $conflict=$locks.Count -gt 1 -or ($manager -and $locks.Count -eq 1 -and $manager -ne $locks[0])
    $candidates=@()
    if ($manager -and -not $conflict) {
        foreach ($action in @('test','build','lint','typecheck','check','verify')) {
            if ($null -ne $scripts -and $null -ne $scripts.PSObject.Properties[$action]) {
                $candidates += New-Candidate ($manager+' run '+$action) ('scripts.'+$action+'; script contents withheld')
            }
        }
    }
    [pscustomobject]@{ language='node'; declared_node=$engine; node_compatibility='NOT_EVALUATED'; package_manager=$manager; package_manager_version=$managerVersion; lockfile_managers=@($locks); conflicting_package_managers=[bool]$conflict; candidates=@($candidates); script_contents='NOT_PRINTED_OR_EXECUTED'; dependency_compatibility='NOT_TESTED' }
}

function Read-MavenManifest([string]$Text,[string[]]$Names) {
    $settings=[Xml.XmlReaderSettings]::new(); $settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit; $settings.XmlResolver=$null
    $source=[IO.StringReader]::new($Text)
    $reader=[Xml.XmlReader]::Create($source,$settings)
    $xml=[Xml.XmlDocument]::new(); $xml.XmlResolver=$null
    try { $xml.Load($reader) } finally { $reader.Dispose(); $source.Dispose() }
    $versions=@()
    foreach ($property in $xml.SelectNodes('/*[local-name()="project"]/*[local-name()="properties"]/*')) {
        if ($property.LocalName -in @('maven.compiler.release','maven.compiler.source','maven.compiler.target','java.version') -and $property.InnerText.Trim() -match '^\d+(?:\.\d+){0,2}$') {
            $versions += [pscustomobject]@{ field=$property.LocalName; value=$property.InnerText.Trim() }
        }
    }
    foreach ($value in $xml.SelectNodes('/*[local-name()="project"]/*[local-name()="build"]/*[local-name()="plugins"]/*[local-name()="plugin"][*[local-name()="artifactId"]="maven-compiler-plugin"]/*[local-name()="configuration"]/*')) {
        if ($value.LocalName -in @('release','source','target') -and $value.InnerText.Trim() -match '^\d+(?:\.\d+){0,2}$') {
            $versions += [pscustomobject]@{ field=('compiler.configuration.'+$value.LocalName); value=$value.InnerText.Trim() }
        }
    }
    $command=if ('mvnw.cmd' -in $Names) { '.\mvnw.cmd test' } elseif ('mvnw' -in $Names) { './mvnw test' } else { 'mvn test' }
    [pscustomobject]@{ language='java'; build_system='maven'; declared_versions=@($versions); effective_toolchain='NOT_EVALUATED'; parents_and_profiles='NOT_RESOLVED'; candidates=@(New-Candidate $command 'pom.xml presence and wrapper filename metadata'); dependency_compatibility='NOT_TESTED' }
}

function Read-GradleManifest([string]$Text,[string[]]$Names) {
    $versions=@()
    $withoutComments=[regex]::Replace($Text,'(?s)/\*.*?\*/','')
    $withoutComments=[regex]::Replace($withoutComments,'(?m)^\s*//.*$','')
    foreach ($match in [regex]::Matches($withoutComments,'(?:JavaLanguageVersion\.of|jvmToolchain)\s*\(\s*(\d+)\s*\)')) {
        $versions += $match.Groups[1].Value
    }
    $command=if ('gradlew.bat' -in $Names) { '.\gradlew.bat test' } elseif ('gradlew' -in $Names) { './gradlew test' } else { 'gradle test' }
    [pscustomobject]@{ language='java'; build_system='gradle'; literal_toolchain_hints=@($versions); effective_toolchain='NOT_EVALUATED'; build_script_execution='NOT_PERFORMED'; candidates=@(New-Candidate $command 'Gradle build filename; literal hints only'); dependency_compatibility='NOT_TESTED' }
}

$records=@(); $issues=@(); $entries=0; $truncated=$false; $links=0
try {
    if ([string]$ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { throw 'LIMITED_LANGUAGE_MODE' }
    $root=Get-Item -LiteralPath $Repository -Force -ErrorAction Stop
    if (-not $root.PSIsContainer -or $null -eq $root.Parent -or $root.Name -in @('.aws','.ssh','.git','.kiro-kit') -or (Test-LinkedPath $root.FullName)) { throw 'INVALID_OR_LINKED_ROOT' }
    $queue=[Collections.Generic.Queue[object]]::new()
    $queue.Enqueue([pscustomobject]@{ path=$root.FullName; depth=0 })
    $excluded=@('.git','.aws','.ssh','.kiro-kit','.venv','venv','node_modules','target','build','dist','.gradle','__pycache__','.tox','.pytest_cache','.mypy_cache','.idea','.vscode')
    while ($queue.Count -gt 0) {
        $directory=$queue.Dequeue()
        $items=@()
        try {
            foreach ($entry in [IO.Directory]::EnumerateFileSystemEntries($directory.path)) {
                if ($entries -ge $MaxEntries) { $truncated=$true; break }
                $entries++
                $item=Get-Item -LiteralPath $entry -Force -ErrorAction Stop
                if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { $links++; continue }
                $items += $item
                if ($item.PSIsContainer -and $item.Name -notin $excluded -and $item.Name -notlike '.venv*') {
                    if ($directory.depth -lt $MaxDepth) { $queue.Enqueue([pscustomobject]@{ path=$item.FullName; depth=$directory.depth+1 }) }
                    else { $truncated=$true }
                }
            }
        } catch { $issues += 'DIRECTORY_NOT_READABLE'; continue }
        $names=@($items | Where-Object { -not $_.PSIsContainer } | ForEach-Object { $_.Name })
        foreach ($file in $items) {
            if ($file.PSIsContainer -or $file.Name -notin @('pyproject.toml','setup.cfg','.python-version','package.json','pom.xml','build.gradle','build.gradle.kts')) { continue }
            $record=[ordered]@{ id=$records.Count+1; manifest=$file.Name; depth=$directory.depth; status='READ'; details=$null }
            if ($IncludeRelativePaths) { $record['relative_path']=$file.FullName.Substring($root.FullName.TrimEnd([IO.Path]::DirectorySeparatorChar).Length+1).Replace('\','/') }
            try {
                $text=Get-SafeText $file
                switch ($file.Name) {
                    'package.json' { $record.details=Read-NodeManifest $text $names }
                    'pom.xml' { $record.details=Read-MavenManifest $text $names }
                    { $_ -in @('build.gradle','build.gradle.kts') } { $record.details=Read-GradleManifest $text $names }
                    '.python-version' {
                        $value=$text.Trim()
                        if ($value -notmatch '^\d+\.\d+(?:\.\d+)?$') { throw 'UNSUPPORTED_PYTHON_VERSION_FILE' }
                        $record.details=[pscustomobject]@{ language='python'; declared_interpreter=$value; python315=if ($value -match '^3\.15(?:\.|$)') { 'SAME_MINOR_DECLARED_ONLY' } else { 'DIFFERENT_INTERPRETER_DECLARED' }; candidates=@() }
                    }
                    default { $record.details=Read-PythonManifest $text $file.Name }
                }
            } catch { $record.status='UNREADABLE_OVERSIZED_OR_UNSUPPORTED'; $record.details=$null }
            $records += [pscustomobject]$record
        }
        if ($entries -ge $MaxEntries) { $truncated=$true; break }
    }
} catch { $issues += 'ROOT_NOT_READABLE_LINKED_OR_LANGUAGE_MODE_UNSUPPORTED' }

[pscustomobject]@{
    format='kiro-repository-inspection-v1'; read_only=$true; commands_executed=0
    entries_examined=$entries; max_depth=$MaxDepth; max_entries=$MaxEntries
    scan_incomplete=($truncated -or $issues.Count -gt 0 -or $links -gt 0 -or @($records | Where-Object status -ne 'READ').Count -gt 0); skipped_links=$links
    unsupported_manifest_count=@($records | Where-Object status -ne 'READ').Count
    records=@($records); issues=@($issues); relative_paths_included=[bool]$IncludeRelativePaths
    repository_compatibility='NOT_VERIFIED'; installation_authorized=$false
    limits='Static hints only. No builds, dependency installs, project scripts, credential files, parent resolution, or complete version-grammar evaluation. File races and hardlink provenance are not qualified.'
} | ConvertTo-Json -Depth 12
