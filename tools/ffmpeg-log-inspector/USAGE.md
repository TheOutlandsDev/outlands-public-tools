# FFmpeg Capture Log Inspector 0.1.0

Download the source ZIP, USAGE.md, VALIDATION.json, build-manifest.json and
SHA256SUMS.txt from the
[same release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ffmpeg-log-inspector-v0.1.0).
Verify every listed asset's SHA-256 before extracting. PowerShell can calculate
a file's digest with `Get-FileHash -Algorithm SHA256 ./ASSET_NAME`; compare its
`Hash` with the corresponding SHA256SUMS.txt entry. On Ubuntu,
`sha256sum -c SHA256SUMS.txt` checks the listed files together. A matching digest
checks equality with that published value; obtain the release through a trusted
route. Extract into an ordinary directory you control.

The source ZIP includes original MIT source, tests, documentation and authored
generators. No PowerShell/.NET runtime, FFmpeg binary or implementation, media,
real log, generated fixture or report is included. The inspector requires only
the supplied `Inspect-FFmpegLog.ps1` and separately obtained PowerShell. The
selected qualification prerequisites are official PowerShell **7.6.10 LTS and
7.7.0 stable**, Windows x64 / Ubuntu x86-64 portable archives recorded in
[RUNTIMES.json](docs/RUNTIMES.json). Windows PowerShell 5.1 is insufficient.
No Python, .NET SDK, module, Pester, FFmpeg installation, online service or
administrator privilege is inherently needed. Corporate execution policy may
restrict scripts; these instructions do not alter or bypass it.

Open PowerShell in the extracted `ffmpeg-log-inspector-0.1.0` folder. Follow the
[private workspace guide](docs/PRIVATE-WORKSPACE.md) to create `$privateWork`
outside the source, then run:

```powershell
pwsh --version
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -Help
$demo = Join-Path $privateWork 'ffmpeg-demo'
pwsh -NoProfile -File ./examples/Make-Demo.ps1 -Destination $demo
$inputLog = Join-Path $demo 'progress-demo.log'
$report = Join-Path $privateWork 'summary.json'
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath $inputLog -ReportPath $report
$inspectionExit = $LASTEXITCODE
$inspectionExit
```

These commands also work in PowerShell on Ubuntu with native absolute paths.
Every generated destination and report filename must be new. The authored
example produces `status: "observations"`, exit **0**, two closed structured
blocks, last frame `60`, last textual media time `2.0` seconds and an observed
`end` marker. These are fictional text observations; no capture occurred.
Omit `-ReportPath` to print JSON without saving a report. The inspector creates
no parent directory and never overwrites an existing report or input.

Try the other authored examples:

```powershell
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath (Join-Path $demo 'stderr-demo.log') -Format Stderr
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath (Join-Path $demo 'review-demo.log') -Format Progress
```

The stderr example produces observations. The review example intentionally
returns exit **1** for decreasing counters and a recognized error phrase.
Preserve `$LASTEXITCODE` immediately after the process when scripting or using
pipelines. Exit **0** means supported numeric observations with none of this
tool's review reasons; **1** means completed inspection with review reasons;
**2** means an input/output, bounds or unsupported-text error and no complete
inspection is claimed. Host or parameter-binding failures can occur outside
the script's JSON error handler. A failed report write may leave a partial new
file; use a fresh destination after resolving the error.

For your own saved log, stop its writer and copy the ordinary stable file to a
private directory you control. Give `-LogPath` a canonical absolute local path;
use `-Format Auto`, `Stderr` or `Progress` with that exact spelling. Relative,
UNC/device and linked/reparse paths are refused. Linked ancestors are refused.
FIFOs, sockets, devices and live pseudo-filesystems are unsupported; portable
.NET checks do not reliably enforce regular-file type on every Unix path.
Native opens and reads have no tool-enforced timeout and may block on an
unsupported file or unresponsive filesystem. The checks are not protection
against adversarial path replacement or a hard process RAM bound.

Read [FORMAT.md](docs/FORMAT.md) before interpreting results. Supported stderr
records start with `frame=` and include a supported `time=` clock; structured
blocks close on `progress=continue` or `progress=end`. Only `frame` and textual
`out_time` are converted. `out_time_ms` and `out_time_us` are counted and ignored
without assuming units. `N/A` is unavailable, not zero. Values are not summed
across records or sessions. Auto keeps the two formats' summaries separate and
requires review when both occur.

An incomplete structured block contributes no committed values. A missing
final `end`, multiple end markers, malformed blocks, missing numeric data,
decreases and selected literal error phrases can require review. Even a final
`progress=end` records text only: it is not a process-exit or capture-success
receipt, playback check, output-duration guarantee or device-health verdict.
Unsupported phrasings can be missed; absence of a recognized phrase does not
prove absence of errors. The inspector never starts FFmpeg, opens media,
captures a device or contacts the network.

Strict UTF-8 accepts one optional initial BOM; CR/LF/CRLF separators and tabs
are supported. ANSI escapes and unsupported control/format characters are
refused. The input bound is 16 MiB, with at most 100,000 segments, 16,384 UTF-16
characters per segment and 128 distinct structured keys per block. Numeric
ceilings are 1,000,000,000,000 frames and 1,000,000,000 media seconds. Fixed regex
matches have 100 ms timeouts. Exceeding a bound fails the inspection instead of
silently truncating it. See [README.md](README.md) and the format for all limits.

Reports omit raw lines, paths, device/file names and unknown values, but retain
the exact input hash, byte size and numeric patterns. Those may identify a
private recording. This is not a secret-removal, anonymity, arbitrary-log
validation or malware-safety tool. Keep real logs/reports private; use a minimal
authored fictional reproduction for a [bug report](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=ffmpeg_log_bug.yml).

Maintainers may run the generated harness with a new private destination:

```powershell
pwsh -NoProfile -File ./tests/Run-Tests.ps1 -WorkRoot (Join-Path $privateWork 'ffmpeg-tests')
```

Python 3.12, 3.13, 3.14 or 3.15.2 is needed only for optional source, build and
qualification helpers. Optimized Python (`-O`/`-OO` or `PYTHONOPTIMIZE`) is
unsupported. See [qualification methods](docs/QUALIFICATION.md), the
[historical validation record](docs/VALIDATION.md), [provenance](docs/PROVENANCE.md)
and [runtime notices](THIRD-PARTY-NOTICES.txt). The release VALIDATION.json records
the actual standalone lane outcomes, exact case counts and explicit skips.
