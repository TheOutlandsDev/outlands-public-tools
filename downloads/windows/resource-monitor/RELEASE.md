# Resource Monitor 0.1.1 - portable Windows x64, package 1

Extract All and double-click **Resource Monitor.cmd** for the fictional dashboard.
Python 3.14.10 is included. **Resource Monitor Live.cmd** separately opts into
actual aggregate metrics using bundled psutil 7.2.1. No pip, runtime installation,
online account, admin rights or PATH changes. [First run](START-HERE.txt).

## Reproduce one useful workflow

Confirm FICTIONAL DEMO, wait for several readings, pause the view and observe the
display hold while the server keeps sampling into bounded memory. Resume to see
current readings. Download JSON/CSV, reopen and inspect them. Stop cleanly, restart
and open the new capability URL: old tokens fail and history starts fresh, while
deliberately downloaded files remain. Export is a file handoff, not import or
history restoration. No settings/database/history files are created automatically.

The separate live launcher opts into actual CPU, memory and aggregate network
counters. Demo startup does not import psutil. First readings and unavailable or
reset counters remain gaps, never substituted valid zeros. Exports contain
operational metrics/timestamps; keep real files and token URLs private.

## Exact source, runtime and dependency

- Original application 0.1.1/source ZIP is unchanged, pinned to
  `42d4490e62c7ffb5d4d40a19e0c27e3ceb2d8897`.
  ZIP SHA-256: `f4123cad35329154fe42a4026f4ed73f3eb739e9f204b311da01b8485199a84b`.
- Official [CPython 3.14.10 Windows x64 embedded runtime](https://www.python.org/downloads/release/python-31410/).
  ZIP SHA-256: `90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`.
  Binary/license bytes stay exact. Only python314._pth adds packaged app/dependency
  search paths; isolated -I -B startup ignores external Python configuration and
  does not write bytecode. No pip or browser is shipped.
- Official [psutil 7.2.1](https://pypi.org/project/psutil/7.2.1/) cp37-abi3-win_amd64
  wheel SHA-256: `b1b0671619343aa71c20ff9767eced0483e4fc9e1f489d50923738caf6a03c17`.
  The entire wheel, including its native module, metadata, LICENSE and verified
  RECORD, is retained unchanged under dependencies/. Default demo never loads it.
- The source-only launcher continues to support Python 3.12/3.13. The new outer
  wrapper directly qualifies the unchanged core/server on current Python 3.14.10.
  Original launcher tests run separately on Python 3.12; they are not skipped or
  altered to bypass its version guard. The old UI footer's v0.1.0 label is retained.

## Qualification and publication

The workflow requires independent Windows/Ubuntu builds with identical ZIP,
receipt and checksum bytes, upstream/source/wheel byte audit, a freshly extracted
package with an isolated bundled interpreter, all 46 original core tests including
real native live sampling, all 49 original source tests separately on Python 3.12,
13 Node presentation tests, and hosted Chromium acceptance for pause/resume,
actual JSON/CSV downloads, stale display, restart and old-token rejection.
The browser export check captures the actual server response with a pass-through
route and delivers its headers/body unchanged, then compares the saved download
byte-for-byte. This avoids an empty Chromium attachment-inspection body; no
fixture response or authentication bypass is substituted.
Only a specifically identified unavailable symlink-creation privilege may be
recorded as a platform skip; live native support is mandatory. The public
acceptance.json records actual counts, skips and completed checks. Configuration
alone is not a pass. All fixture and live metrics, tokens, local paths, downloaded
files, screenshots and raw logs remain private; only counts and named outcomes
are published. Live checks record pass/fail without exposing measurements.

The new separate release never replaces source ZIPs or older assets. Its public
SHA256SUMS.txt covers the ZIP, release receipt and sanitized acceptance. Exact
application/runtime/dependency and packaging source revisions are recorded.

## Contribution and limits

The original project/provenance and AI-assistance disclosure remain inspectable.
This work adds a runtime handoff, two explicit mode launchers, package verification
and end-to-end qualification around unchanged application code. It keeps the
separation between observed values, missing data, fictional fixtures and claims
about platform support.

Windows 11 x64 is the target; hosted automated acceptance is separate from a
human using Explorer and their default browser on a Python-free PC. That manual
test remains unperformed. Other architectures/OS runtime bundles, physical phones,
other browsers, calibrated hardware accuracy, production diagnosis and power-loss
recovery remain unqualified. The outer ZIP/CMD is unsigned. Checksums do not
establish signatures, sandboxing or independent upstream-code review.

History is intentionally memory-only. Pause freezes the tab, not the sampler;
export reads current bounded server history. Browser filename/overwrite choices
follow browser behavior; original explicit CLI exports refuse existing paths.
There is no automatic saving, history import, remote hosting or service setup.
Read the [original limits](../../../tools/resource-monitor/docs/VALIDATION.md)
and retain the [source ZIP alternative](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/resource-monitor-v0.1.1).
