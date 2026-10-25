#requires -Version 7.2
<#
.SYNOPSIS
Summarizes supported progress observations in an existing UTF-8 FFmpeg log.
#>
[CmdletBinding()]
param([string]$LogPath, [string]$ReportPath, [string]$Format = 'Auto', [switch]$Help)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($Help) {
    Write-Output 'Usage: pwsh -NoProfile -File Inspect-FFmpegLog.ps1 -LogPath ABS.log [-ReportPath NEW.json] [-Format Auto|Stderr|Progress]'
    Write-Output 'Offline text observations only. Exit 0: supported observations; 1: review needed; 2: input/output or processing failure. Neither 0 nor progress=end proves recording success.'
    exit 0
}
$script:errorCode = 'input_or_output_error'
function Stop-Inspection([string]$Code) { $script:errorCode = $Code; throw [System.IO.InvalidDataException]::new($Code) }
function Make-Regex([string]$Pattern, [bool]$IgnoreCase = $false) {
    $options = [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    if ($IgnoreCase) { $options = $options -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase }
    return [regex]::new($Pattern, $options, [TimeSpan]::FromMilliseconds(100))
}
function Local-Path([string]$Path, [bool]$InputFile) {
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path.Length -gt 4096 -or -not [IO.Path]::IsPathFullyQualified($Path) -or $Path.StartsWith('\\') -or $Path.StartsWith('//')) { Stop-Inspection 'absolute_local_path_required' }
    if ((Make-Regex '[\p{Cc}\p{Cf}]').IsMatch($Path)) { Stop-Inspection 'control_in_path' }
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -cne $Path -or $Path.Contains('::') -or ($IsWindows -and $Path.Substring(2).Contains(':'))) { Stop-Inspection 'canonical_local_path_required' }
    $current = if ($InputFile) {$full} else {[IO.Path]::GetDirectoryName($full)}
    if (-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($full))) { Stop-Inspection 'existing_parent_required' }
    while (-not [string]::IsNullOrEmpty($current)) {
        $info = if ([IO.Directory]::Exists($current)) {[IO.DirectoryInfo]::new($current)} else {[IO.FileInfo]::new($current)}
        if (-not $info.Exists) { Stop-Inspection 'regular_input_required' }
        if (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $null -ne $info.LinkTarget) { Stop-Inspection 'linked_path_rejected' }
        $current = [IO.Path]::GetDirectoryName($current)
    }
    if ($InputFile -and -not [IO.File]::Exists($full)) { Stop-Inspection 'regular_input_required' }
    return $full
}
function Read-Snapshot([string]$Path) {
    $full = Local-Path $Path $true
    $inputStream = [IO.File]::Open($full, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $size = $inputStream.Length
        if ($size -gt 16777216) { Stop-Inspection 'log_byte_limit' }
        $stamp = [IO.File]::GetLastWriteTimeUtc($full)
        $data = [byte[]]::new([int]$size); $offset = 0
        while ($offset -lt $data.Length) {
            $read = $inputStream.Read($data, $offset, $data.Length - $offset)
            if ($read -eq 0) { Stop-Inspection 'input_changed' }
            $offset += $read
        }
        if ($inputStream.ReadByte() -ne -1 -or $inputStream.Length -ne $size -or [IO.File]::GetLastWriteTimeUtc($full) -ne $stamp) { Stop-Inspection 'input_changed' }
        return ,$data
    } finally { $inputStream.Dispose() }
}
function Parse-Frame([string]$Token) {
    if ($Token -ceq 'N/A') { return @{valid=$true;value=$null} }
    if (-not $script:integer.IsMatch($Token)) { return @{valid=$false;value=$null} }
    $value = [long]::Parse($Token, [Globalization.CultureInfo]::InvariantCulture)
    return @{valid=($value -le 1000000000000L);value=$value}
}
function Parse-Time([string]$Token) {
    if ($Token -ceq 'N/A') { return @{valid=$true;value=$null} }
    $match = $script:clock.Match($Token)
    if (-not $match.Success) { return @{valid=$false;value=$null} }
    $hours = [long]::Parse($match.Groups['hours'].Value, [Globalization.CultureInfo]::InvariantCulture)
    $minutes = [long]::Parse($match.Groups['minutes'].Value, [Globalization.CultureInfo]::InvariantCulture)
    $seconds = [long]::Parse($match.Groups['seconds'].Value, [Globalization.CultureInfo]::InvariantCulture)
    $fraction = if ($match.Groups['fraction'].Success) {[decimal]::Parse($match.Groups['fraction'].Value.PadRight(6,'0'),[Globalization.CultureInfo]::InvariantCulture) / 1000000D} else {0D}
    $value = [decimal]($hours * 3600L + $minutes * 60L + $seconds) + $fraction
    return @{valid=($value -le 1000000000D);value=$value}
}
function New-Stats {
    return [ordered]@{records=0;numericFields=0;frameObservations=0;timeObservations=0;unavailableFrames=0;unavailableTimes=0;lastFrame=$null;maximumFrame=$null;lastTimeSeconds=$null;maximumTimeSeconds=$null;frameDecreases=0;timeDecreases=0}
}
function Add-Observation($Stats, $Frame, $Time) {
    $Stats.records++
    if ($null -ne $Frame) {
        if ($null -eq $Frame.value) {$Stats.unavailableFrames++}
        else {
            if ($null -ne $Stats.lastFrame -and $Frame.value -lt $Stats.lastFrame) {$Stats.frameDecreases++}
            $Stats.lastFrame = $Frame.value; $Stats.frameObservations++; $Stats.numericFields++
            if ($null -eq $Stats.maximumFrame -or $Frame.value -gt $Stats.maximumFrame) {$Stats.maximumFrame=$Frame.value}
        }
    }
    if ($null -ne $Time) {
        if ($null -eq $Time.value) {$Stats.unavailableTimes++}
        else {
            if ($null -ne $Stats.lastTimeSeconds -and $Time.value -lt $Stats.lastTimeSeconds) {$Stats.timeDecreases++}
            $Stats.lastTimeSeconds = $Time.value; $Stats.timeObservations++; $Stats.numericFields++
            if ($null -eq $Stats.maximumTimeSeconds -or $Time.value -gt $Stats.maximumTimeSeconds) {$Stats.maximumTimeSeconds=$Time.value}
        }
    }
}
function Has-Literal([string]$Text, [string]$Literal) { return $Text.IndexOf($Literal, [StringComparison]::OrdinalIgnoreCase) -ge 0 }

$reader = $null
try {
    if (@('Auto','Stderr','Progress') -cnotcontains $Format) { Stop-Inspection 'format_invalid' }
    $data = Read-Snapshot $LogPath
    $utf8 = [Text.UTF8Encoding]::new($false,$true)
    $text = $utf8.GetString($data)
    if ($text.Length -gt 0 -and [int]$text[0] -eq 0xfeff) {$text=$text.Substring(1)}
    $script:integer = Make-Regex '\A[0-9]{1,13}\z'
    $script:clock = Make-Regex '\A(?<hours>[0-9]{2,6}):(?<minutes>[0-5][0-9]):(?<seconds>[0-5][0-9])(?:\.(?<fraction>[0-9]{1,6}))?\z'
    $control = Make-Regex '[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\p{Cf}]'
    $stderrCandidate = Make-Regex '\A\s*frame\s*='
    $stderrFrame = Make-Regex '(?:\A|\s)frame\s*=\s*(?<value>\S+)'
    $stderrTime = Make-Regex '(?:\A|\s)time\s*=\s*(?<value>\S+)'
    $keyValue = Make-Regex '\A(?<key>[A-Za-z0-9_]{1,64})=(?<value>[^\r\n]*)\z'
    $multipleTokens = Make-Regex '\S+\s+\S'
    $stderrStats = New-Stats; $progressStats = New-Stats
    $counts = [ordered]@{segments=0;nonemptySegments=0;ignoredSegments=0;stderrCandidates=0;malformedStderrRecords=0;structuredKeyValueSegments=0;ignoredStructuredKeys=0;closedStructuredBlocks=0;invalidStructuredBlocks=0;unterminatedStructuredBlock=$false;duplicateStructuredKeys=0;continueMarkers=0;endMarkers=0;lastMarker=$null}
    $signals = [ordered]@{inputOutputError=0;openError=0;filterError=0;deviceLost=0;conversionFailed=0;decodeError=0}
    $keys = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $frame=$null; $time=$null; $blockInvalid=$false; $blockOpen=$false
    $reader = [IO.StringReader]::new($text)
    while ($null -ne ($line = $reader.ReadLine())) {
        $counts.segments++
        if ($counts.segments -gt 100000) { Stop-Inspection 'segment_count_limit' }
        if ($line.Length -gt 16384) { Stop-Inspection 'segment_character_limit' }
        if ($control.IsMatch($line)) { Stop-Inspection 'unsupported_control_character' }
        if ([string]::IsNullOrWhiteSpace($line)) {continue}
        $counts.nonemptySegments++
        if (Has-Literal $line 'Input/output error') {$signals.inputOutputError++}
        if ((Has-Literal $line 'Error opening') -or (Has-Literal $line 'Could not open') -or (Has-Literal $line 'Failed to open')) {$signals.openError++}
        if ((Has-Literal $line 'Could not run filter') -or (Has-Literal $line 'Error reinitializing filters')) {$signals.filterError++}
        if ((Has-Literal $line 'device') -and (Has-Literal $line 'lost')) {$signals.deviceLost++}
        if (Has-Literal $line 'Conversion failed!') {$signals.conversionFailed++}
        if (Has-Literal $line 'Error while decoding') {$signals.decodeError++}
        $kv = $keyValue.Match($line)
        $looksLikeStderr = $stderrCandidate.IsMatch($line) -and $kv.Success -and $multipleTokens.IsMatch($kv.Groups['value'].Value.Trim())
        if ($Format -cne 'Stderr' -and $kv.Success -and ($Format -ceq 'Progress' -or -not $looksLikeStderr)) {
            $key=$kv.Groups['key'].Value; $value=$kv.Groups['value'].Value.Trim()
            $counts.structuredKeyValueSegments++; $blockOpen=$true
            if (-not $keys.Add($key)) {$counts.duplicateStructuredKeys++;$blockInvalid=$true}
            if ($keys.Count -gt 128) {Stop-Inspection 'structured_key_limit'}
            switch -CaseSensitive ($key) {
                'frame' {$frame=Parse-Frame $value;if(-not $frame.valid){$blockInvalid=$true}}
                'out_time' {$time=Parse-Time $value;if(-not $time.valid){$blockInvalid=$true}}
                'progress' {
                    $counts.closedStructuredBlocks++
                    if ($value -ceq 'continue') {$counts.continueMarkers++;$counts.lastMarker='continue'}
                    elseif ($value -ceq 'end') {$counts.endMarkers++;$counts.lastMarker='end'}
                    else {$blockInvalid=$true;$counts.lastMarker='unsupported'}
                    if ($blockInvalid) {$counts.invalidStructuredBlocks++}
                    else {Add-Observation $progressStats $frame $time}
                    $keys.Clear();$frame=$null;$time=$null;$blockInvalid=$false;$blockOpen=$false
                }
                default {$counts.ignoredStructuredKeys++}
            }
            continue
        }
        if ($Format -cne 'Progress' -and $stderrCandidate.IsMatch($line)) {
            $counts.stderrCandidates++
            $frames=$stderrFrame.Matches($line);$times=$stderrTime.Matches($line)
            if ($frames.Count -ne 1 -or $times.Count -ne 1) {$counts.malformedStderrRecords++;continue}
            $fm=$frames[0];$tm=$times[0]
            $sf=Parse-Frame $fm.Groups['value'].Value; $st=Parse-Time $tm.Groups['value'].Value
            if (-not $sf.valid -or -not $st.valid) {$counts.malformedStderrRecords++;continue}
            Add-Observation $stderrStats $sf $st
            continue
        }
        $counts.ignoredSegments++
        # Non-key text inside an open progress block cannot be called a clean block.
        if ($blockOpen) {$blockInvalid=$true}
    }
    $counts.unterminatedStructuredBlock=$blockOpen
    $reasons=[Collections.Generic.List[string]]::new()
    if ($stderrStats.numericFields + $progressStats.numericFields -eq 0) {$reasons.Add('no_supported_numeric_progress')}
    if ($counts.malformedStderrRecords -gt 0) {$reasons.Add('malformed_stderr_records')}
    if ($counts.invalidStructuredBlocks -gt 0) {$reasons.Add('invalid_structured_blocks')}
    if ($blockOpen) {$reasons.Add('unterminated_structured_block')}
    if ($counts.structuredKeyValueSegments -gt 0 -and $counts.lastMarker -cne 'end') {$reasons.Add('no_final_end_marker')}
    if ($counts.endMarkers -gt 1) {$reasons.Add('multiple_end_markers')}
    if ($stderrStats.records -gt 0 -and $progressStats.records -gt 0) {$reasons.Add('mixed_progress_formats')}
    if ($stderrStats.frameDecreases + $stderrStats.timeDecreases + $progressStats.frameDecreases + $progressStats.timeDecreases -gt 0) {$reasons.Add('counter_decrease_observed')}
    if (($signals.Values | Measure-Object -Sum).Sum -gt 0) {$reasons.Add('recognized_error_phrase')}
    $report=[ordered]@{schemaVersion=1;tool='ffmpeg-log-inspector';status=$(if($reasons.Count -eq 0){'observations'}else{'review'});requestedFormat=$Format;input=[ordered]@{bytes=$data.LongLength;sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($data)).ToLowerInvariant()};coverage=$counts;stderrProgress=$stderrStats;structuredProgress=$progressStats;signalSegments=$signals;reviewReasons=$reasons.ToArray();interpretation='Observed supported text only. Counters, error phrases and progress=end do not prove recording success, media quality, elapsed wall time, device health or root cause. Other text and unsupported keys are not interpreted.'}
    $json=$report|ConvertTo-Json -Depth 8
    if (-not [string]::IsNullOrEmpty($ReportPath)) {
        $outputPath=Local-Path $ReportPath $false
        $output=[IO.File]::Open($outputPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$bytes=$utf8.GetBytes($json+"`n");$output.Write($bytes,0,$bytes.Length)}finally{$output.Dispose()}
    }
    Write-Output $json
    if ($reasons.Count -gt 0) {exit 1};exit 0
} catch [Text.RegularExpressions.RegexMatchTimeoutException] {
    [ordered]@{schemaVersion=1;tool='ffmpeg-log-inspector';status='error';error='regex_time_limit';coverage='No complete report.'}|ConvertTo-Json
    exit 2
} catch {
    [ordered]@{schemaVersion=1;tool='ffmpeg-log-inspector';status='error';error=$script:errorCode;coverage='No complete report.'}|ConvertTo-Json
    exit 2
} finally {if($null -ne $reader){$reader.Dispose()}}
