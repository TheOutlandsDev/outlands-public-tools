#requires -Version 7.2
<#
.SYNOPSIS
Checks a local ZIP against an explicit JSON policy without extracting it.
#>
[CmdletBinding()]
param([string]$ArchivePath, [string]$PolicyPath, [string]$ReportPath, [switch]$Help)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($Help) {
    Write-Output 'Usage: pwsh -NoProfile -File Test-ZipPackagePolicy.ps1 -ArchivePath ABS.zip -PolicyPath ABS.json [-ReportPath NEW.json]'
    Write-Output 'Exit 0: policy passed; 1: policy findings; 2: invalid input or incomplete inspection. See README.md for scope and privacy.'
    exit 0
}
$script:code = 'invalid_input'
function Stop-Check([string]$Code) { $script:code = $Code; throw [System.IO.InvalidDataException]::new($Code) }
function Require-Fields($Object, [string[]]$Allowed, [string[]]$Required) {
    if ($Object.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) { Stop-Check 'policy_object_required' }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($property in $Object.EnumerateObject()) {
        if (-not $seen.Add($property.Name)) { Stop-Check 'policy_duplicate_field' }
        if ($Allowed -cnotcontains $property.Name) { Stop-Check 'policy_unknown_field' }
    }
    foreach ($name in $Required) { if (-not $seen.Contains($name)) { Stop-Check 'policy_missing_field' } }
}
function Get-Number($Value, [long]$Minimum, [long]$Maximum) {
    $number = [long]0
    if ($Value.ValueKind -ne [System.Text.Json.JsonValueKind]::Number -or -not $Value.TryGetInt64([ref]$number) -or $number -lt $Minimum -or $number -gt $Maximum) { Stop-Check 'policy_invalid_integer' }
    return $number
}
function Test-MemberName([string]$Name, [bool]$AllowDirectory) {
    if ([string]::IsNullOrEmpty($Name) -or $Name.Length -gt 1024 -or $Name.Contains('\') -or $Name.Contains(':') -or $Name.StartsWith('/') -or $Name -match '[\x00-\x1f\x7f-\x9f<>"|?*\p{Cf}]') { return $false }
    $clean = $Name
    if ($clean.EndsWith('/')) { if (-not $AllowDirectory) { return $false }; $clean = $clean.Substring(0, $clean.Length - 1) }
    foreach ($part in $clean.Split('/')) {
        if ($part -eq '' -or $part -eq '.' -or $part -eq '..' -or $part.EndsWith('.') -or $part.EndsWith(' ')) { return $false }
        if ($part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') { return $false }
    }
    return $true
}
function Get-StringArray($Value, [bool]$Members) {
    if ($Value.ValueKind -ne [System.Text.Json.JsonValueKind]::Array -or $Value.GetArrayLength() -gt 4096) { Stop-Check 'policy_invalid_array' }
    $result = [System.Collections.Generic.List[string]]::new()
    $unique = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($item in $Value.EnumerateArray()) {
        if ($item.ValueKind -ne [System.Text.Json.JsonValueKind]::String) { Stop-Check 'policy_string_required' }
        $valueText = $item.GetString()
        if ($valueText.Length -eq 0 -or $valueText.Length -gt $(if ($Members) {1024} else {4096}) -or $valueText -match '[\x00\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]') { Stop-Check 'policy_invalid_string' }
        if ($Members -and -not (Test-MemberName $valueText $false)) { Stop-Check 'policy_unsafe_member' }
        if (-not $unique.Add($valueText)) { Stop-Check 'policy_duplicate_value' }
        $result.Add($valueText)
    }
    return ,$result.ToArray()
}
function Get-LocalPath([string]$Path, [bool]$MustExist) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [System.IO.Path]::IsPathFullyQualified($Path) -or $Path.StartsWith('\\') -or $Path.StartsWith('//')) { Stop-Check 'local_absolute_path_required' }
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full -cne $Path -or $Path.Contains('::') -or ($IsWindows -and $Path.Substring(2).Contains(':'))) { Stop-Check 'canonical_local_path_required' }
    $current = if ($MustExist) { $full } else { [System.IO.Path]::GetDirectoryName($full) }
    if (-not [System.IO.Directory]::Exists([System.IO.Path]::GetDirectoryName($full))) { Stop-Check 'parent_directory_required' }
    while (-not [string]::IsNullOrEmpty($current)) {
        $info = if ([System.IO.Directory]::Exists($current)) { [System.IO.DirectoryInfo]::new($current) } else { [System.IO.FileInfo]::new($current) }
        if (-not $info.Exists) { Stop-Check 'input_file_required' }
        if (($info.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or $null -ne $info.LinkTarget) { Stop-Check 'linked_path_rejected' }
        $parent = [System.IO.Path]::GetDirectoryName($current)
        if ($parent -eq $current) { break }; $current = $parent
    }
    if ($MustExist -and -not [System.IO.File]::Exists($full)) { Stop-Check 'input_file_required' }
    return $full
}
function Read-Snapshot([string]$Path, [long]$Maximum) {
    $full = Get-LocalPath $Path $true
    $stream = [System.IO.File]::Open($full, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        $length = $stream.Length
        if ($length -gt $Maximum) { Stop-Check 'input_size_limit' }
        $stamp = [System.IO.File]::GetLastWriteTimeUtc($full)
        $buffer = [byte[]]::new([int]$length)
        $offset = 0
        while ($offset -lt $buffer.Length) { $read = $stream.Read($buffer, $offset, $buffer.Length - $offset); if ($read -eq 0) { Stop-Check 'input_changed' }; $offset += $read }
        if ($stream.ReadByte() -ne -1 -or $stream.Length -ne $length -or [System.IO.File]::GetLastWriteTimeUtc($full) -ne $stamp) { Stop-Check 'input_changed' }
        return ,$buffer
    } finally { $stream.Dispose() }
}
function Check-ZipEnvelope([byte[]]$Bytes, [int]$MaxEntries) {
    # Limit central-directory metadata before ZipArchive materializes its entries.
    if ($Bytes.Length -lt 22) { Stop-Check 'zip_invalid_structure' }
    $found = -1
    for ($i = $Bytes.Length - 22; $i -ge [Math]::Max(0, $Bytes.Length - 65557); $i--) {
        if ([BitConverter]::ToUInt32($Bytes, $i) -eq 0x06054b50 -and $i + 22 + [BitConverter]::ToUInt16($Bytes, $i + 20) -eq $Bytes.Length) { $found = $i; break }
    }
    if ($found -lt 0) { Stop-Check 'zip_invalid_structure' }
    $count = [BitConverter]::ToUInt16($Bytes, $found + 10)
    $centralSize = [BitConverter]::ToUInt32($Bytes, $found + 12)
    $centralOffset = [BitConverter]::ToUInt32($Bytes, $found + 16)
    if ([BitConverter]::ToUInt16($Bytes, $found + 4) -ne 0 -or [BitConverter]::ToUInt16($Bytes, $found + 6) -ne 0 -or [BitConverter]::ToUInt16($Bytes, $found + 8) -ne $count -or $count -eq 65535 -or $centralSize -eq [uint32]::MaxValue -or $centralOffset -eq [uint32]::MaxValue) { Stop-Check 'zip_multidisk_or_zip64_unsupported' }
    if ($count -gt $MaxEntries -or $centralSize -gt 8388608) { Stop-Check 'zip_metadata_limit' }
    if ([long]$centralOffset + $centralSize -ne $found) { Stop-Check 'zip_invalid_structure' }
    $position = [long]$centralOffset
    $localOffsets = [System.Collections.Generic.HashSet[long]]::new()
    for ($entryIndex = 0; $entryIndex -lt $count; $entryIndex++) {
        if ($position + 46 -gt $found -or [BitConverter]::ToUInt32($Bytes, [int]$position) -ne 0x02014b50) { Stop-Check 'zip_invalid_structure' }
        $flags = [BitConverter]::ToUInt16($Bytes, [int]$position + 8)
        $method = [BitConverter]::ToUInt16($Bytes, [int]$position + 10)
        if (($flags -band 0x2041) -ne 0 -or $method -notin @(0,8)) { Stop-Check 'zip_encryption_or_method_unsupported' }
        $nameLength = [BitConverter]::ToUInt16($Bytes, [int]$position + 28)
        $extraLength = [BitConverter]::ToUInt16($Bytes, [int]$position + 30)
        $commentLength = [BitConverter]::ToUInt16($Bytes, [int]$position + 32)
        $localOffset = [BitConverter]::ToUInt32($Bytes, [int]$position + 42)
        if ([BitConverter]::ToUInt16($Bytes, [int]$position + 34) -ne 0 -or $localOffset -ge $centralOffset -or $localOffset + 30 -gt $Bytes.Length -or [BitConverter]::ToUInt32($Bytes, [int]$localOffset) -ne 0x04034b50) { Stop-Check 'zip_invalid_structure' }
        if ($position + 46 + $nameLength + $extraLength + $commentLength -gt $found -or -not $localOffsets.Add($localOffset)) { Stop-Check 'zip_invalid_structure' }
        $localNameLength = [BitConverter]::ToUInt16($Bytes, [int]$localOffset + 26)
        $localExtraLength = [BitConverter]::ToUInt16($Bytes, [int]$localOffset + 28)
        $compressedSize = [BitConverter]::ToUInt32($Bytes, [int]$position + 20)
        if ($compressedSize -eq [uint32]::MaxValue -or [BitConverter]::ToUInt32($Bytes, [int]$position + 24) -eq [uint32]::MaxValue -or $localOffset + 30 + $localNameLength + $localExtraLength + $compressedSize -gt $centralOffset -or $localNameLength -ne $nameLength -or [BitConverter]::ToUInt16($Bytes, [int]$localOffset + 6) -ne $flags -or [BitConverter]::ToUInt16($Bytes, [int]$localOffset + 8) -ne $method) { Stop-Check 'zip_invalid_structure' }
        for ($nameIndex=0; $nameIndex -lt $nameLength; $nameIndex++) { if ($Bytes[$localOffset + 30 + $nameIndex] -ne $Bytes[$position + 46 + $nameIndex]) { Stop-Check 'zip_local_name_mismatch' } }
        if (($flags -band 8) -eq 0) { foreach ($pair in @(@(14,16),@(18,20),@(22,24))) { if ([BitConverter]::ToUInt32($Bytes, [int]$localOffset + $pair[0]) -ne [BitConverter]::ToUInt32($Bytes, [int]$position + $pair[1])) { Stop-Check 'zip_local_metadata_mismatch' } } }
        # Reject ZIP64 extra records even when legacy fields do not use sentinels.
        $extraEnd = $position + 46 + $nameLength + $extraLength
        $extraPosition = $position + 46 + $nameLength
        while ($extraPosition -lt $extraEnd) {
            if ($extraPosition + 4 -gt $extraEnd) { Stop-Check 'zip_invalid_structure' }
            $kind = [BitConverter]::ToUInt16($Bytes, [int]$extraPosition)
            $size = [BitConverter]::ToUInt16($Bytes, [int]$extraPosition + 2)
            if ($kind -eq 1) { Stop-Check 'zip_multidisk_or_zip64_unsupported' }
            $extraPosition += 4 + $size
            if ($extraPosition -gt $extraEnd) { Stop-Check 'zip_invalid_structure' }
        }
        $position += 46 + $nameLength + $extraLength + $commentLength
    }
    if ($position -ne $found -or ($count -eq 0 -and $centralOffset -ne 0) -or ($count -gt 0 -and -not $localOffsets.Contains(0))) { Stop-Check 'zip_invalid_structure' }
}

$jsonDocument = $null; $zip = $null; $memory = $null
try {
    $policyBytes = Read-Snapshot $PolicyPath 1048576
    $utf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $policyText = $utf8.GetString($policyBytes)
    $options = [System.Text.Json.JsonDocumentOptions]::new(); $options.MaxDepth = 16
    $jsonDocument = [System.Text.Json.JsonDocument]::Parse($policyText, $options)
    $policy = $jsonDocument.RootElement
    Require-Fields $policy @('schemaVersion','requiredMembers','forbiddenMembers','allowedMembers','expectedSha256','expectedSize','limits','textRules') @('schemaVersion')
    if ((Get-Number $policy.GetProperty('schemaVersion') 1 1) -ne 1) { Stop-Check 'policy_schema_unsupported' }
    $properties = @($policy.EnumerateObject() | ForEach-Object Name)
    $required = @(); $forbidden = @(); $allowed = $null; $textRules = @()
    if ($properties -ccontains 'requiredMembers') { $required = Get-StringArray $policy.GetProperty('requiredMembers') $true }
    if ($properties -ccontains 'forbiddenMembers') { $forbidden = Get-StringArray $policy.GetProperty('forbiddenMembers') $true }
    if ($properties -ccontains 'allowedMembers') { $allowed = Get-StringArray $policy.GetProperty('allowedMembers') $true }
    foreach ($member in $required) { if ($forbidden -ccontains $member -or ($null -ne $allowed -and $allowed -cnotcontains $member)) { Stop-Check 'policy_contradictory_members' } }
    $limits = @{maxEntries=4096; maxTotalUncompressedBytes=268435456L; maxMemberBytes=67108864L; maxTextBytes=262144L}
    if ($properties -ccontains 'limits') {
        $limitObject = $policy.GetProperty('limits'); Require-Fields $limitObject @($limits.Keys) @()
        foreach ($property in $limitObject.EnumerateObject()) { $limits[$property.Name] = Get-Number $property.Value 1 $limits[$property.Name] }
    }
    $expectedHash = $null; $expectedSize = $null
    if ($properties -ccontains 'expectedSha256') { $hashValue = $policy.GetProperty('expectedSha256'); if ($hashValue.ValueKind -ne [System.Text.Json.JsonValueKind]::String -or $hashValue.GetString() -cnotmatch '\A[0-9a-fA-F]{64}\z') { Stop-Check 'policy_invalid_sha256' }; $expectedHash = $hashValue.GetString().ToLowerInvariant() }
    if ($properties -ccontains 'expectedSize') { $expectedSize = Get-Number $policy.GetProperty('expectedSize') 0 67108864 }
    if ($properties -ccontains 'textRules') {
        $rulesObject = $policy.GetProperty('textRules')
        if ($rulesObject.ValueKind -ne [System.Text.Json.JsonValueKind]::Array -or $rulesObject.GetArrayLength() -gt 64) { Stop-Check 'policy_invalid_text_rules' }
        $ruleMembers = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        foreach ($rule in $rulesObject.EnumerateArray()) {
            Require-Fields $rule @('member','containsAll','containsNone') @('member')
            $ruleNameObject = $rule.GetProperty('member')
            if ($ruleNameObject.ValueKind -ne [System.Text.Json.JsonValueKind]::String) { Stop-Check 'policy_string_required' }
            $ruleName = $ruleNameObject.GetString()
            if (-not (Test-MemberName $ruleName $false) -or -not $ruleMembers.Add($ruleName)) { Stop-Check 'policy_invalid_text_member' }
            $ruleProperties = @($rule.EnumerateObject() | ForEach-Object Name)
            $containsAll = @(); $containsNone = @()
            if ($ruleProperties -ccontains 'containsAll') { $containsAll = Get-StringArray $rule.GetProperty('containsAll') $false }
            if ($ruleProperties -ccontains 'containsNone') { $containsNone = Get-StringArray $rule.GetProperty('containsNone') $false }
            if ($containsAll.Count + $containsNone.Count -eq 0 -or $containsAll.Count + $containsNone.Count -gt 256) { Stop-Check 'policy_invalid_text_rules' }
            foreach ($marker in $containsAll) { if ($containsNone -ccontains $marker) { Stop-Check 'policy_contradictory_text' } }
            $textRules += @{member=$ruleName; containsAll=$containsAll; containsNone=$containsNone}
        }
    }
    $archiveBytes = Read-Snapshot $ArchivePath 67108864
    Check-ZipEnvelope $archiveBytes $limits.maxEntries
    $sha256 = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($archiveBytes)).ToLowerInvariant()
    $findings = [System.Collections.Generic.List[object]]::new()
    function Add-Finding([string]$Code, [string]$Member = '') { $item = [ordered]@{code=$Code}; if ($Member -ne '') { $item.member=$Member }; $findings.Add($item) }
    if ($null -ne $expectedSize -and $archiveBytes.LongLength -ne $expectedSize) { Add-Finding 'archive_size_mismatch' }
    if ($null -ne $expectedHash -and $sha256 -cne $expectedHash) { Add-Finding 'archive_sha256_mismatch' }
    $memory = [System.IO.MemoryStream]::new($archiveBytes, $false)
    $zip = [System.IO.Compression.ZipArchive]::new($memory, [System.IO.Compression.ZipArchiveMode]::Read, $true, $utf8)
    if ($zip.Entries.Count -gt $limits.maxEntries) { Stop-Check 'zip_metadata_limit' }
    $names = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $portableNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $files = [System.Collections.Generic.Dictionary[string,object]]::new([System.StringComparer]::Ordinal)
    $allNames = [System.Collections.Generic.List[string]]::new()
    $total = [long]0
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        if (-not (Test-MemberName $name $true)) { Stop-Check 'zip_unsafe_member_name' }
        $key = $name.TrimEnd('/').Normalize([System.Text.NormalizationForm]::FormC)
        if (-not $names.Add($name) -or -not $portableNames.Add($key)) { Stop-Check 'zip_duplicate_or_portable_collision' }
        $unixType = ($entry.ExternalAttributes -shr 16) -band 0xf000
        if ($unixType -notin @(0,0x8000,0x4000) -or ($entry.ExternalAttributes -band 0x400) -ne 0) { Stop-Check 'zip_special_member_rejected' }
        if ($entry.Length -gt $limits.maxMemberBytes -or $entry.Length -lt 0) { Stop-Check 'zip_member_size_limit' }
        $total += $entry.Length
        if ($total -gt $limits.maxTotalUncompressedBytes) { Stop-Check 'zip_total_size_limit' }
        if ($name.EndsWith('/')) { if ($entry.Length -ne 0 -or $unixType -eq 0x8000) { Stop-Check 'zip_inconsistent_directory' } }
        else { if ($unixType -eq 0x4000) { Stop-Check 'zip_inconsistent_directory' }; $files.Add($name, $entry) }
        $allNames.Add($name)
    }
    $portableFiles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($name in $files.Keys) { [void]$portableFiles.Add($name.Normalize([System.Text.NormalizationForm]::FormC)) }
    foreach ($name in $allNames) {
        $components = $name.TrimEnd('/').Split('/'); $prefix = ''
        for ($partIndex=0; $partIndex -lt $components.Length - 1; $partIndex++) { $prefix = if ($prefix -eq '') {$components[$partIndex]} else {$prefix + '/' + $components[$partIndex]}; if ($portableFiles.Contains($prefix.Normalize([System.Text.NormalizationForm]::FormC))) { Stop-Check 'zip_file_directory_collision' } }
    }
    foreach ($name in $required) { if (-not $files.ContainsKey($name)) { Add-Finding 'required_member_missing' $name } }
    foreach ($name in $forbidden) { if ($files.ContainsKey($name)) { Add-Finding 'forbidden_member_present' $name } }
    [string[]]$orderedFiles = @($files.Keys); [Array]::Sort($orderedFiles, [StringComparer]::Ordinal)
    if ($null -ne $allowed) { foreach ($name in $orderedFiles) { if ($allowed -cnotcontains $name) { Add-Finding 'member_not_allowed' $name } } }
    $textBytesRead = [long]0
    foreach ($rule in $textRules) {
        if (-not $files.ContainsKey($rule.member)) { Add-Finding 'text_member_missing' $rule.member; continue }
        $entry = $files[$rule.member]
        if ($entry.Length -gt $limits.maxTextBytes -or $textBytesRead + $entry.Length -gt 1048576) { Stop-Check 'zip_text_size_limit' }
        $contentStream = $entry.Open(); $textMemory = [System.IO.MemoryStream]::new()
        try {
            $chunk = [byte[]]::new(8192)
            while (($read = $contentStream.Read($chunk,0,$chunk.Length)) -gt 0) {
                if ($textMemory.Length + $read -gt $limits.maxTextBytes -or $textBytesRead + $read -gt 1048576) { Stop-Check 'zip_text_size_limit' }
                $textMemory.Write($chunk,0,$read); $textBytesRead += $read
            }
            if ($textMemory.Length -ne $entry.Length) { Stop-Check 'zip_text_length_mismatch' }
            $content = $utf8.GetString($textMemory.ToArray())
            foreach ($marker in $rule.containsAll) { if (-not $content.Contains($marker, [System.StringComparison]::Ordinal)) { Add-Finding 'required_literal_missing' $rule.member } }
            foreach ($marker in $rule.containsNone) { if ($content.Contains($marker, [System.StringComparison]::Ordinal)) { Add-Finding 'forbidden_literal_present' $rule.member } }
        } finally { $contentStream.Dispose(); $textMemory.Dispose() }
    }
    $report = [ordered]@{schemaVersion=1; tool='zip-package-policy'; status=$(if ($findings.Count -eq 0) {'pass'} else {'findings'}); archive=[ordered]@{bytes=$archiveBytes.LongLength;sha256=$sha256;entries=$zip.Entries.Count;files=$files.Count;declaredUncompressedBytes=$total}; inspectedTextBytes=$textBytesRead; findings=$findings.ToArray(); coverage='Metadata and selected literal UTF-8 text only; other content and CRCs were not verified.'}
    $exitCode = if ($findings.Count -eq 0) {0} else {1}
    $json = $report | ConvertTo-Json -Depth 12
    if (-not [string]::IsNullOrEmpty($ReportPath)) {
        $fullOutput = Get-LocalPath $ReportPath $false
        $output = [System.IO.File]::Open($fullOutput, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try { $outputBytes=$utf8.GetBytes($json + "`n"); $output.Write($outputBytes,0,$outputBytes.Length) } finally {$output.Dispose()}
    }
    Write-Output $json
    exit $exitCode
} catch {
    [ordered]@{schemaVersion=1;tool='zip-package-policy';status='error';error=$script:code;coverage='Inspection did not complete.'} | ConvertTo-Json -Depth 4
    exit 2
} finally { if ($null -ne $zip) {$zip.Dispose()}; if ($null -ne $memory) {$memory.Dispose()}; if ($null -ne $jsonDocument) {$jsonDocument.Dispose()} }
