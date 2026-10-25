# OUTLANDS | FFmpeg Capture Log Inspector

Read an existing UTF-8 FFmpeg text log and summarize supported frame/time
observations, counter decreases, progress markers and selected error phrases.
This original MIT PowerShell utility performs **offline text inspection**. It
does not start FFmpeg, open media, capture a camera/microphone or contact a device.

It generalizes the log-reading mechanism of the owner's local capture-test
helper. The public source, tests and examples are freshly authored and contain
no original captures, device names, private paths or FFmpeg implementation.
See [provenance and license scope](docs/PROVENANCE.md).

## Requirements and first example

Use **PowerShell 7.2 or newer** (`pwsh --version`) on Windows or Linux. No modules,
Pester, FFmpeg installation, Python runtime or online service is required by the
CLI. Clone/download the collection and open a terminal in
`tools/ffmpeg-log-inspector`. Keep inputs and reports in a separate
[private workspace](../../docs/PRIVATE-WORKSPACE.md).

Set `$privateWork` to an existing absolute local directory you control. Use
`Join-Path` so paths have the native separator. Demo/output destinations must be
new, canonical absolute paths under existing parents.

```powershell
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -Help
$demo = Join-Path $privateWork 'ffmpeg-demo'
pwsh -NoProfile -File ./examples/Make-Demo.ps1 -Destination $demo
$inputLog = Join-Path $demo 'progress-demo.log'
$report = Join-Path $privateWork 'ffmpeg-summary.json'
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath $inputLog -ReportPath $report
```

The fictional progress example exits **0**, reports two closed blocks, last frame
`60`, textual media time `2.0` seconds and an observed `end` marker. It creates a
fresh JSON report. These observations are generated data, not capture evidence.
Omit `-ReportPath` to print only JSON without writing a report. Existing reports
are never replaced; the output parent must already exist.

Try the other generated examples:

```powershell
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath (Join-Path $demo 'stderr-demo.log') -Format Stderr
pwsh -NoProfile -File ./Inspect-FFmpegLog.ps1 -LogPath (Join-Path $demo 'review-demo.log') -Format Progress
```

The first reports two stderr progress observations. The second exits **1** with
counter-decrease and error-phrase review reasons. Nonzero **1** is an expected
finding result, not a parser crash. Preserve the process exit code in pipelines.

## Supported text

- **Stderr records:** lines/CR updates beginning with `frame=`, with a supported
  nonnegative integer or `N/A` frame value and a whitespace-separated `time=`
  clock value. Other statistics are not interpreted.
- **Structured progress:** `key=value` segments ending in `progress=continue` or
  `progress=end`. Only `frame` and textual `out_time` become numeric observations.
  Extra keys are counted and ignored. In particular, `out_time_ms` and
  `out_time_us` are **not converted**; the tool makes no unit assumption for them.
- **Auto** (default) recognizes these subsets and keeps their summaries separate.
  Mixed observed formats require review. Use `-Format Stderr` or
  `-Format Progress` when you know the input's source.

The [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html#Main-options) describes
periodic statistics and structured progress blocks. This tool supports the
specific subset in [FORMAT.md](docs/FORMAT.md), not every FFmpeg version, verbose
log layout, wrapper prefix, localized diagnostic or arbitrary application log.
CR, LF and CRLF separators are supported; ANSI terminal escape sequences and
other unsupported control/format characters are rejected rather than rendered.

## Results and interpretation

| Exit | Status | Meaning |
| --- | --- | --- |
| `0` | `observations` | Supported numeric observations were found with none of this tool's review reasons. This is not a success or health verdict. |
| `1` | `review` | Missing supported data, malformed/partial blocks, decreasing counters, mixed formats, multiple/end-marker issues or recognized phrases need review. |
| `2` | `error` | Input/output failed, bounds were exceeded or text was unsupported. No complete report is claimed. |

`N/A` is unavailable, not zero. Last values and maxima are separate; values are
not summed across records or log sessions. Decreases may indicate resets,
concatenated logs or another cause; this tool does not determine which. A valid
`progress=end` only records that text. It does not prove process exit status,
successful encoding, correct output duration, a playable file or camera health.
Likewise, absence of a supported phrase does not establish absence of errors.
Ignored-segment/key counts expose text outside the supported interpretation.

Reports include the selected log's byte length and SHA-256, numeric observations,
fixed signal names and coverage counts. They omit raw lines, file/device names,
input/output paths and unknown key/value text. Hashes and timing/count patterns
can still identify a private log. Keep real reports private until reviewed; this
is not an anonymity or secret-removal tool. Raw logs may contain credentials or
private media URLs and should not be attached to public issues.

## File and processing boundaries

Inputs must be ordinary, stable, trusted local files under directories you
control. UNC/device paths, existing symbolic links/reparse points, relative paths
and noncanonical paths are rejected. Stop log writers before reading. Windows
file sharing prevents ordinary concurrent writers while the snapshot is read;
length/time checks detect some other changes. This is not an atomic snapshot or
a sandbox against adversarial path replacement.

Portable .NET checks do not reliably enforce regular-file type on every Unix
path. FIFOs, sockets, devices and live pseudo-filesystems are unsupported. Native
file opens/reads have no tool-enforced timeout and may block on unsupported
files or an unresponsive filesystem. Use copied ordinary files only.

Hard bounds are **16 MiB** per input, **100,000** segments, **16,384 UTF-16
characters** per segment, **128** distinct structured keys per block,
**1,000,000,000,000** frames and **1,000,000,000** media seconds. Fixed regexes
have 100 ms match timeouts. Strict UTF-8 accepts an optional initial BOM. Limits
fail the complete inspection; they never silently truncate it. A new report may
remain partial after an output-write error, but existing files are untouched.

## Tests and suggestions

```powershell
pwsh -NoProfile -File ./tests/Run-Tests.ps1 -WorkRoot (Join-Path $privateWork 'ffmpeg-log-tests')
python -B source_check.py
```

The first command uses only generated logs and bounded child CLI processes and
retains its fictional artifacts in the new test directory. The optional source
gate uses Python 3.12/3.13 to verify the published source manifest; Python is not
a CLI dependency. See [validation](docs/VALIDATION.md) and the
[contribution guide](CONTRIBUTING.md).

[Report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=ffmpeg_log_bug.yml)
or [suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=ffmpeg_log_suggestion.yml).
Include PowerShell/OS versions and a minimal fictional log. Suggestions for
documented formats, clearer coverage and portability are welcome. This module's
original source, documentation and generated fixtures use the [MIT license](LICENSE).
