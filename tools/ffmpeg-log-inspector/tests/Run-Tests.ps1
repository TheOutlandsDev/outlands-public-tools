#requires -Version 7.2
param([string]$WorkRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([string]::IsNullOrWhiteSpace($WorkRoot) -or -not [IO.Path]::IsPathFullyQualified($WorkRoot)) {throw 'WorkRoot must be an absolute new private directory.'}
$root=[IO.Path]::GetFullPath($WorkRoot)
if ($root -cne $WorkRoot -or [IO.File]::Exists($root) -or [IO.Directory]::Exists($root) -or -not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($root))) {throw 'WorkRoot must be new with an existing parent.'}
[void][IO.Directory]::CreateDirectory($root)
$module=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$scriptPath=Join-Path $module 'Inspect-FFmpegLog.ps1'
$pwsh=(Get-Process -Id $PID).Path
$script:count=0
$utf8=[Text.UTF8Encoding]::new($false)
function Assert([bool]$Condition,[string]$Message) {if(-not $Condition){throw $Message}}
function New-Log([string]$Name,[string]$Text) {$path=Join-Path $root ($Name+'.log');[IO.File]::WriteAllText($path,$Text,$utf8);return $path}
function Hash([string]$Path) {return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($Path)))}
function Invoke-Cli([string[]]$Arguments,[string]$Entry=$scriptPath) {
    $start=[Diagnostics.ProcessStartInfo]::new();$start.FileName=$pwsh;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true;$start.CreateNoWindow=$true
    foreach($item in @('-NoProfile','-File',$Entry)+$Arguments){[void]$start.ArgumentList.Add($item)}
    $process=[Diagnostics.Process]::new();$process.StartInfo=$start
    try {
        [void]$process.Start();$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
        if(-not $process.WaitForExit(30000)){$process.Kill($true);throw 'Fixture CLI exceeded 30 seconds.'}
        return @{code=$process.ExitCode;text=$stdout.GetAwaiter().GetResult();error=$stderr.GetAwaiter().GetResult()}
    } finally {$process.Dispose()}
}
function Check-Case([string]$Name,[string]$Path,[int]$Code,[scriptblock]$Inspect,[string[]]$Extra=@(),[string]$Entry=$scriptPath) {
    $before=if([IO.File]::Exists($Path)){Hash $Path}else{$null}
    $result=Invoke-Cli (@('-LogPath',$Path)+$Extra) $Entry
    Assert ($result.code -eq $Code) ($Name+': exit '+$result.code+' '+$result.error+' '+$result.text)
    Assert ([string]::IsNullOrWhiteSpace($result.error)) ($Name+': unexpected stderr')
    $report=$result.text|ConvertFrom-Json -Depth 12
    if($null-ne $before){Assert ((Hash $Path)-ceq $before) ($Name+': input changed');if($Code -ne 2){Assert ($report.input.sha256 -ceq $before.ToLowerInvariant()) ($Name+': snapshot hash')}}
    if($null-ne $Inspect){& $Inspect $report $result.text}
    $script:count++;Write-Output ('PASS '+$Name)
}
$stderr=New-Log 'stderr' "frame= 30 fps=30.0 time=00:00:01.250 bitrate=N/A`rframe= 60 fps=30 time=00:00:02.500 bitrate=N/A`n"
Check-Case 'stderr no BOM preserves first character and CR records' $stderr 0 {param($r) Assert ($r.stderrProgress.records -eq 2 -and $r.stderrProgress.lastFrame -eq 60 -and $r.stderrProgress.lastTimeSeconds -eq 2.5) 'stderr observations';Assert ($r.coverage.structuredKeyValueSegments -eq 0) 'stderr separation'}
$progress=New-Log 'progress' "frame=30`nout_time=00:00:01.000001`nprogress=continue`nframe=60`nout_time=00:00:02.500000`nprogress=end`n"
Check-Case 'closed structured blocks' $progress 0 {param($r) Assert ($r.structuredProgress.records -eq 2 -and $r.coverage.endMarkers -eq 1 -and $r.structuredProgress.lastTimeSeconds -eq 2.5) 'structured observations'}
Check-Case 'zero counters are observations' (New-Log 'zero' "frame=0`nout_time=00:00:00.000000`nprogress=end") 0 {param($r) Assert ($r.structuredProgress.lastFrame -eq 0 -and $r.structuredProgress.lastTimeSeconds -eq 0 -and $r.structuredProgress.numericFields -eq 2) 'zero is available'}
Check-Case 'explicit stderr mode' $stderr 0 {param($r) Assert ($r.requestedFormat -ceq 'Stderr') 'explicit format'} @('-Format','Stderr')
Check-Case 'explicit progress mode' $progress 0 {param($r) Assert ($r.requestedFormat -ceq 'Progress') 'explicit format'} @('-Format','Progress')
$bom=Join-Path $root 'bom.log';[IO.File]::WriteAllBytes($bom,([byte[]]@(0xef,0xbb,0xbf)+[IO.File]::ReadAllBytes($progress)))
Check-Case 'one UTF8 BOM' $bom 0 {param($r) Assert ($r.structuredProgress.lastFrame -eq 60) 'BOM parsing'}
Check-Case 'CRLF supported' (New-Log 'crlf' "frame=1`r`nout_time=00:00:00.1`r`nprogress=end`r`n") 0 {param($r) Assert ($r.coverage.segments -eq 3) 'CRLF segment count'}
Check-Case 'final segment need not end in newline' (New-Log 'no-newline' "frame=1`nout_time=00:00:00.1`nprogress=end") 0 {param($r) Assert ($r.coverage.lastMarker -ceq 'end') 'EOF marker'}
Check-Case 'missing final marker' (New-Log 'unfinished' "frame=1`nout_time=00:00:00.1") 1 {param($r) Assert ($r.reviewReasons -contains 'unterminated_structured_block') 'partial block';Assert ($r.structuredProgress.records -eq 0) 'no partial values committed'}
Check-Case 'continue without end' (New-Log 'continue' "frame=1`nout_time=00:00:00.1`nprogress=continue`n") 1 {param($r) Assert ($r.reviewReasons -contains 'no_final_end_marker') 'end missing'}
Check-Case 'duplicate structured fields discard block' (New-Log 'duplicate' "frame=1`nframe=2`nout_time=00:00:00.1`nprogress=end`n") 1 {param($r) Assert ($r.coverage.duplicateStructuredKeys -eq 1 -and $r.structuredProgress.records -eq 0) 'duplicate refusal'}
Check-Case 'invalid final marker' (New-Log 'bad-marker' "frame=1`nprogress=done`n") 1 {param($r) Assert ($r.coverage.invalidStructuredBlocks -eq 1 -and $r.coverage.lastMarker -ceq 'unsupported') 'unsupported marker'}
Check-Case 'unknown keys and ambiguous numeric time units ignored' (New-Log 'ignored' "frame=1`nout_time_ms=9999999`nout_time_us=7777777`nprivate_label=/fictional/recording.mov`nout_time=00:00:00.125`nprogress=end`n") 0 {param($r,$text) Assert ($r.coverage.ignoredStructuredKeys -eq 3 -and $r.structuredProgress.lastTimeSeconds -eq 0.125) 'supported time only';Assert (-not $text.Contains('recording.mov')) 'private value leaked'}
Check-Case 'N/A counters remain unavailable' (New-Log 'unavailable' "frame=N/A`nout_time=N/A`nprogress=end`n") 1 {param($r) Assert ($r.structuredProgress.unavailableFrames -eq 1 -and $r.structuredProgress.unavailableTimes -eq 1 -and $null-eq $r.structuredProgress.lastFrame) 'unavailable is not zero'}
Check-Case 'audio style textual time without frame' (New-Log 'audio' "out_time=00:00:03.25`nprogress=end`n") 0 {param($r) Assert ($null-eq $r.structuredProgress.lastFrame -and $r.structuredProgress.lastTimeSeconds -eq 3.25) 'audio time'}
Check-Case 'stderr unavailable time' (New-Log 'stderr-na' "frame=1 fps=0 time=N/A bitrate=N/A`n") 0 {param($r) Assert ($r.stderrProgress.unavailableTimes -eq 1 -and $r.stderrProgress.lastFrame -eq 1) 'stderr unavailable'}
Check-Case 'last numeric observation survives later N/A explicitly' (New-Log 'later-na' "frame=7`nout_time=00:00:00.5`nprogress=continue`nframe=N/A`nout_time=N/A`nprogress=end") 0 {param($r) Assert ($r.structuredProgress.lastFrame -eq 7 -and $r.structuredProgress.lastTimeSeconds -eq 0.5 -and $r.structuredProgress.unavailableFrames -eq 1 -and $r.structuredProgress.unavailableTimes -eq 1) 'last available semantics'}
Check-Case 'frame and time decreases observed separately' (New-Log 'decrease' "frame=10`nout_time=00:00:02.0`nprogress=continue`nframe=2`nout_time=00:00:01.0`nprogress=end`n") 1 {param($r) Assert ($r.structuredProgress.frameDecreases -eq 1 -and $r.structuredProgress.timeDecreases -eq 1 -and $r.structuredProgress.maximumFrame -eq 10 -and $r.structuredProgress.lastFrame -eq 2) 'decrease summary'}
Check-Case 'stderr decrease observed' (New-Log 'stderr-decrease' "frame=10 time=00:00:02`nframe=1 time=00:00:01`n") 1 {param($r) Assert ($r.stderrProgress.frameDecreases -eq 1) 'stderr counter decrease'}
Check-Case 'mixed formats not merged' (New-Log 'mixed' "frame=5 fps=0 time=00:00:05`nframe=1`nout_time=00:00:01`nprogress=end`n") 1 {param($r) Assert ($r.reviewReasons -contains 'mixed_progress_formats') 'mixed warning';Assert ($r.stderrProgress.lastFrame -eq 5 -and $r.structuredProgress.lastFrame -eq 1) 'separate counters'}
Check-Case 'multiple end markers' (New-Log 'multi-end' "frame=1`nprogress=end`nframe=2`nprogress=end`n") 1 {param($r) Assert ($r.coverage.endMarkers -eq 2 -and $r.reviewReasons -contains 'multiple_end_markers') 'multiple markers'}
Check-Case 'empty input' (New-Log 'empty' '') 1 {param($r) Assert ($r.coverage.segments -eq 0 -and $r.reviewReasons -contains 'no_supported_numeric_progress') 'empty coverage'}
Check-Case 'unrecognized text is not healthy evidence' (New-Log 'banner' "Fictional banner and metadata only`n") 1 {param($r) Assert ($r.coverage.ignoredSegments -eq 1) 'ignored count'}
Check-Case 'signal kinds omit raw text' (New-Log 'signals' "frame=1 time=00:00:00.1`nInput/output error: /fictional/private.mov`nError opening file`nCould not run filter`nDevice was lost`nConversion failed!`nError while decoding stream`n") 1 {param($r,$text) Assert ($r.signalSegments.inputOutputError -eq 1 -and $r.signalSegments.openError -eq 1 -and $r.signalSegments.filterError -eq 1 -and $r.signalSegments.deviceLost -eq 1 -and $r.signalSegments.conversionFailed -eq 1 -and $r.signalSegments.decodeError -eq 1) 'signal counts';Assert (-not $text.Contains('private.mov')) 'raw signal leaked'}
foreach($pair in @(@('bad-frame','x','00:00:01'),@('negative-frame','-1','00:00:01'),@('frame-overflow','9999999999999999999999','00:00:01'),@('bad-minutes','1','00:60:00'),@('negative-time','1','-00:00:01'),@('comma-time','1','00:00:01,5'),@('nan-time','1','nan'),@('precision','1','00:00:01.1234567'),@('time-overflow','1','999999:59:59'))){Check-Case $pair[0] (New-Log $pair[0] ('frame='+$pair[1]+' time='+$pair[2])) 1 {param($r) Assert ($r.coverage.malformedStderrRecords -eq 1 -and $r.stderrProgress.records -eq 0) 'malformed data discarded'}}
Check-Case 'missing stderr time' (New-Log 'no-time' 'frame=1 fps=30 bitrate=N/A') 1 {param($r) Assert ($r.coverage.malformedStderrRecords -eq 1) 'missing time'}
Check-Case 'duplicate stderr frame is ambiguous' (New-Log 'duplicate-stderr-frame' 'frame=1 time=00:00:01 frame=2') 1 {param($r) Assert ($r.coverage.malformedStderrRecords -eq 1 -and $r.stderrProgress.records -eq 0) 'duplicate frame discarded'}
Check-Case 'duplicate stderr time is ambiguous' (New-Log 'duplicate-stderr-time' 'frame=1 time=00:00:01 time=00:00:02') 1 {param($r) Assert ($r.coverage.malformedStderrRecords -eq 1 -and $r.stderrProgress.records -eq 0) 'duplicate time discarded'}
Check-Case 'explicit progress foreign text invalidates open block' (New-Log 'interleave' "frame=1`nFictional interrupted line`nprogress=end") 1 {param($r) Assert ($r.coverage.invalidStructuredBlocks -eq 1) 'interrupted block'} @('-Format','Progress')
Check-Case 'auto foreign text invalidates open block' (New-Log 'interleave-auto' "frame=1`nFictional interrupted line`nprogress=end") 1 {param($r) Assert ($r.coverage.invalidStructuredBlocks -eq 1 -and $r.structuredProgress.records -eq 0) 'auto interrupted block'}
Check-Case 'case-sensitive format option' $progress 2 {param($r) Assert ($r.error -ceq 'format_invalid') 'invalid option'} @('-Format','progress')
Check-Case 'relative input refused' 'relative.log' 2 {param($r) Assert ($r.error -ceq 'absolute_local_path_required') 'relative path'}
Check-Case 'missing input refused' (Join-Path $root 'absent.log') 2 {param($r) Assert ($r.error -ceq 'regular_input_required') 'absent path'}
Check-Case 'directory input refused' $root 2 {param($r) Assert ($r.error -ceq 'regular_input_required') 'directory path'}
foreach($pair in @(@('nul',0),@('escape',27),@('bidi',0x202e))){Check-Case $pair[0] (New-Log $pair[0] ('frame=1 time=00:00:01'+[char]$pair[1])) 2 {param($r) Assert ($r.error -ceq 'unsupported_control_character') 'unsupported control'}}
$invalid=Join-Path $root 'invalid-utf8.log';[IO.File]::WriteAllBytes($invalid,[byte[]]@(0xff,0xfe));Check-Case 'invalid UTF8' $invalid 2 {param($r) Assert ($r.error -ceq 'input_or_output_error') 'strict decoding'}
Check-Case 'long segment bound' (New-Log 'long' ('x'*16385)) 2 {param($r) Assert ($r.error -ceq 'segment_character_limit') 'segment bound'}
Check-Case 'segment count bound' (New-Log 'many' ("`n"*100001)) 2 {param($r) Assert ($r.error -ceq 'segment_count_limit') 'count bound'}
$large=Join-Path $root 'large.log';$stream=[IO.File]::Create($large);$stream.SetLength(16777217);$stream.Dispose();Check-Case 'input byte bound' $large 2 {param($r) Assert ($r.error -ceq 'log_byte_limit') 'byte bound'}
$keys=(1..129|ForEach-Object {'key'+$_+'=x'})-join "`n";Check-Case 'per-block key bound' (New-Log 'keys' $keys) 2 {param($r) Assert ($r.error -ceq 'structured_key_limit') 'key bound'}
$output=Join-Path $root 'report.json';Check-Case 'fresh report' $progress 0 {param($r) Assert ([IO.File]::Exists($output)) 'new output'} @('-ReportPath',$output)
$outputHash=Hash $output;Check-Case 'existing report retained' $progress 2 {param($r) Assert ((Hash $output)-ceq $outputHash) 'report overwritten'} @('-ReportPath',$output)
Check-Case 'input cannot be output' $progress 2 $null @('-ReportPath',$progress)
$cultureScript=Join-Path $root 'culture.ps1';[IO.File]::WriteAllText($cultureScript,('[Globalization.CultureInfo]::CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo(''fr-FR'')'+"`n"+'& '+"'"+$scriptPath.Replace("'","''")+"' @args`n"+'exit $LASTEXITCODE'),$utf8)
Check-Case 'decimal parsing invariant under French culture' $progress 0 {param($r) Assert ($r.structuredProgress.lastTimeSeconds -eq 2.5) 'culture changed value'} @() $cultureScript
$help=Invoke-Cli @('-Help');Assert ($help.code -eq 0 -and $help.text.Contains('Usage:')) 'help';$script:count++;Write-Output 'PASS help without inputs'
$link=Join-Path $root 'linked.log'
try {[void][IO.File]::CreateSymbolicLink($link,$progress)}catch {if(-not $IsWindows -or $env:OUTLANDS_REQUIRE_SYMLINK_TEST -eq '1'){throw};Write-Output 'SKIP symbolic-link fixture: native Windows privilege unavailable.'}
if([IO.File]::Exists($link)){Check-Case 'linked input refused' $link 2 {param($r) Assert ($r.error -ceq 'linked_path_rejected') 'linked input'}}
Write-Output ('PASS total='+$script:count+'; all inspected input hashes unchanged; generated fixtures retained only in WorkRoot.')
