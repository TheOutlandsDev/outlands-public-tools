# OUTLANDS | Keep Awake

Selected Windows keep-awake source with an optional animated Tk interface. It requests that the system and display stay awake using SetThreadExecutionState. The visual field is deterministic animation, not AI inference. The retained script identifies itself as Awake Horizon 6.1.2; that identifier is preserved source context, not a newly validated release claim.

## Runtime and commands

Use Windows Python 3.12 or 3.13 for runtime operation; visual mode also requires Tk/Tcl. Console mode does not import Tkinter. No third-party Python runtime package, interpreter, DLL, font, installer, configuration or real input data is bundled. Native Windows/Python 3.12.7 and Tk 8.6 request/lifecycle fixtures now pass; read the [Windows validation contract](docs/WINDOWS.md) and [current review](../../docs/BATCH-24-KEEP-AWAKE-WINDOWS.md). API success is not actual sleep/display-policy acceptance.

From this tool directory:

```text
python keep_awake.py --help
python keep_awake.py --version
python keep_awake.py --no-visual --minutes 15
python keep_awake.py --minutes 15
```

The first two commands show static information without acquiring a power request. Non-Windows runtime/self-test invocation returns status 1 with WINDOWS_REQUIRED before attempting native APIs. Malformed arguments return status 2 and ARGUMENTS_INVALID without echoing supplied values. Help/version use a static program name, not a local script pathname. Durations must be nonnegative, finite and convertible to finite seconds.

`--minutes 0` is the default and runs until exit. The display request is enabled in both console and visual modes. Theme, quality, fullscreen and frame-rate options affect visual mode. Legacy `--minimized`, `--pattern` and `--keep-display-on` are accepted for compatibility but do not change behavior; they do not minimize the interface or disable the display request.

## Stopping and cleanup

Close the window or press Ctrl+Q to stop visual mode; Ctrl+C stops console mode. F11 toggles fullscreen, Escape or N returns to windowed mode and M selects the next monitor. These bindings belong to the application, not global keyboard hooks. Fullscreen is borderless/topmost and hides its cursor/hints; it is not a locked session or privacy screen.

The script clears its thread's keep-awake flags during cleanup. A failed clear call leaves a local active flag and emits a fixed warning. An unconfirmed clear returns status 1 with RESTORATION_NOT_CONFIRMED; GUI clear failures remain failures even if a later cleanup retry succeeds. Cleanup text reports an attempt, not proof of the machine's final sleep behavior. Requests must be refreshed/cleared on their creating Python thread. This is a standalone application, not an independent request handle or a composable/nested request manager for other code on that thread.

GUI roots and the app timer are cleaned up after startup failures, mainloop exit, window closing or smoke-test paths. Tk callback failures and periodic power-request failures close the application and return status 1 with GUI_CALLBACK_FAILED or POWER_REQUEST_FAILED. They do not open a blocking error dialog. Handled CLI/self-test failures and restoration warnings use fixed categories without printing exception values or tracebacks. Catastrophic interpreter/native failures, forced termination and external Tcl diagnostics are outside this handled-error boundary; keep captures private.

A native API result or local bookkeeping flag is not end-to-end system acceptance. Close programs normally, read warnings and validate the expected behavior on the intended machine. Keeping a system/display awake uses additional energy.

## Scope and API limits

The selected script does not move the mouse, synthesize keyboard input, change power plans, register persistence, read documents/credentials or use a network client. Source/runtime captures can still expose surrounding machine details; this is not an anonymity tool.

Microsoft documents this API as controlling system/display idle requirements; it cannot block user-initiated sleep and does not stop screen savers. See [SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate). The source does not provide a session-lock/security-policy guarantee. Native monitor geometry, mixed DPI, topmost behavior, timer timing and controller/power-policy interactions require real Windows acceptance.

`--self-test` calls real Windows monitor/power APIs. `--ui-smoke-test` also creates transparent Tk objects and a power request, renders 60 animation frames and exercises fullscreen/windowed transitions. Both were run in the current Windows review, including with `python -O`; their checks remain active under optimization. These are opt-in runtime operations, not passive source review or physical sleep-policy tests. Reported frame timing is a local smoke measurement, not a performance guarantee.

## Recorded validation

Current local Windows/Python 3.12.7: **56 methods passed, zero failures/errors/skips**. The original 27 remain synthetic; one fake app now explicitly provides its lifecycle interface. The new 29 contain 14 portable failure checks and 15 opt-in Windows power/Tk cases. Native tests verify successful API results, an independent previous-thread-state probe, bounded console runs, Python SIGINT cleanup, real monitor enumeration, registered window closing, deadlines, loop quit, callback/startup failures and real frame smoke tests. Injected API/GUI failures are labeled fault fixtures; they are not naturally occurring OS failures. Mixed DPI and actual idle sleep were not accepted.

A separate single-file package copy passed **16 fresh processes**: 13 direct CLI invocations, including normal/optimized console/self-test/Tk smoke commands, and three instrumented native processes for a console Tk-import barrier, Python SIGINT and a callback fault. Runtime/source bytes stayed unchanged and no bytecode appeared. Captures remain private. Dedicated CI runs Python 3.12/3.13 on Windows/Ubuntu; Windows native cases must execute without skips, while Ubuntu runs portable checks and skips the 15 Windows-only cases.

The earlier reference result below is historical, not a statement that the new review avoided native calls.

**27 unittest methods passed, zero failures/errors/skips**, on isolated Python 3.12.7/Linux. Coverage includes helpers, bounded durations, private argument/help/version output, platform guards, deterministic graph data, simulated power flags/acquisition/restore failures, interrupted cleanup, fake-clock console timing and fake Tk startup/close paths. Twelve failures/errors in the prior sanitized copy were reproduced and corrected; the baseline's other fifteen methods already passed.

Windows DLL loads are guarded against accidental native use; power functions are fakes, Tk modules/roots are fake and clocks/sleep are mocked where loops run. No real Windows API, display, power setting, monitor enumeration, self-test/UI-smoke-test command, dependency installation or original-drive program was exercised. These tests validate selected Python control flow; they do not establish Windows, GUI rendering, power restoration, frame-rate or multi-monitor acceptance.

Run portable/synthetic tests from this directory; native tests are explicitly skipped:

```text
python -B -m unittest discover -s tests -v
```

To opt into short real Windows request/Tk tests from PowerShell:

```powershell
$env:OUTLANDS_AWAKE_NATIVE = '1'
python -B -m unittest discover -s tests -v
Remove-Item Env:OUTLANDS_AWAKE_NATIVE
```

The native fixture opt-in does not change normal application commands. Read the [test boundary and remaining manual checks](docs/WINDOWS.md).

## Provenance and licensing

The owner reports personal work created with AI assistance. This candidate comes from the retained, hash-verified sanitized source packet and its historical source mapping. The original drive path was unavailable for a fresh source hash check during this review; that gap is recorded rather than treated as unchanged-source proof. Public corrections, tests and documentation were AI-assisted. No required attribution, copyright or license notice was removed. These records are not independent proof of exclusive authorship or every original influence.

Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). See [the source review](../../docs/BATCH-5-REVIEW.md) for the exact validation boundary. No private audit record, original source history, runtime captures or other Programs folders are included.
