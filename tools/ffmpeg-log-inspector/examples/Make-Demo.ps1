#requires -Version 7.2
param([string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([string]::IsNullOrWhiteSpace($Destination) -or -not [IO.Path]::IsPathFullyQualified($Destination)) {throw 'An absolute new destination is required.'}
$target=[IO.Path]::GetFullPath($Destination)
if ($target -cne $Destination -or [IO.File]::Exists($target) -or [IO.Directory]::Exists($target) -or -not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($target))) {throw 'Use a canonical new destination under an existing private parent.'}
$current=[IO.Path]::GetDirectoryName($target)
while (-not [string]::IsNullOrEmpty($current)) {
    $info=[IO.DirectoryInfo]::new($current)
    if (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $null -ne $info.LinkTarget) {throw 'Linked parents are unsupported.'}
    $current=[IO.Path]::GetDirectoryName($current)
}
[void][IO.Directory]::CreateDirectory($target)
$encoding=[Text.UTF8Encoding]::new($false)
$examples=@{
    'stderr-demo.log'="Fictional Orchard capture log; no media was captured.`nframe=   30 fps=30.0 q=-1.0 size=N/A time=00:00:01.000000 bitrate=N/A speed=1x`rframe=   60 fps=30.0 q=-1.0 size=N/A time=00:00:02.000000 bitrate=N/A speed=1x`n"
    'progress-demo.log'="frame=30`nfps=30.0`nout_time_us=1000000`nout_time=00:00:01.000000`nprogress=continue`nframe=60`nout_time=00:00:02.000000`nprogress=end`n"
    'review-demo.log'="frame=30`nout_time=00:00:01.000000`nprogress=continue`nInput/output error on fictional source`nframe=20`nout_time=00:00:00.500000`nprogress=end`n"
}
foreach($name in $examples.Keys) {
    $stream=[IO.File]::Open((Join-Path $target $name),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$bytes=$encoding.GetBytes($examples[$name]);$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
Write-Output 'Created three fictional logs; no FFmpeg process, media file, device or network access was used.'
