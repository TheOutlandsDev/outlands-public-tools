# Keep Awake Windows contract

Use the existing public MIT script with Windows Python 3.12/3.13; Tk/Tcl is
needed only for visual operation. No install, external input, configuration,
document, user record, network request or bundled runtime is needed. Native
tests deliberately create short system/display requests and transparent Tk
windows. Keep machine/runtime captures outside GitHub.

## Requests and cleanup

The binding uses `ctypes.c_uint` for the argument and previous-state result of
[SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
Acquire/refresh uses `0x80000003` (continuous, system and display required);
clear uses `0x80000000`. A nonzero result means the call succeeded and contains
the preceding thread state. Failure diagnostics do not interpret an unspecified
last-error value or echo native exception text.

The application uses one creating Python thread. Calls from another thread
are rejected before changing flags. The local `active` flag becomes false only
after a successful clear. The API affects thread flags, not a separate
reference-counted request object: embedding/nesting other requests on the same
thread is unsupported. Closing a console forcibly is not a graceful Python
cleanup test.

Normal completion and Python interruption attempt cleanup. A failed clear
emits a fixed warning and preserves uncertainty. GUI cleanup failures return
failure even if context cleanup later retries successfully. API-return and
local-flag checks do not prove that the display turns off or the system sleeps.
The API cannot block user-initiated sleep or the screen saver, and the utility
does not establish session-lock/security-policy behavior.

## GUI failures and self-tests

The Tk callback reporter is installed before constructing the app. Callback
exceptions close the app with `GUI_CALLBACK_FAILED`; a periodic request failure
closes with `POWER_REQUEST_FAILED`. There is no modal failure dialog containing
exception details. App cleanup also runs after an external mainloop quit,
canceling its timer before root destruction. Startup failures destroy any
created root, and ordinary window closing is idempotent.

`--self-test` and `--ui-smoke-test` use explicit runtime checks; `python -O`
does not remove them or the monitor-transition operations. The UI smoke test
creates a transparent window, renders 60 frames and checks fullscreen/windowed
transitions. Switching monitors is conditional on actual monitor availability.
Timing and a successful Tk call are not visual-quality or frame-rate acceptance.

Handled CLI errors use fixed categories; unknown exception values become
`RUNTIME_FAILED`. The original parser still withholds invalid argument values
and local program paths. Native crashes, forced termination, external Tcl
diagnostics and the surrounding interpreter/terminal are outside this boundary.

## Evidence

Local Windows/Python 3.12.7 with Tk 8.6: original 27 synthetic methods and new
29 methods all passed, no failures/errors/skips. The new set has 14 portable
and 15 opt-in Windows cases. Independent native calls observed the expected
previous flags after acquisition and continuous-only flags after cleanup.
Tests restore their test thread's preceding flags, do not alter power plans,
and do not suspend, reboot, lock, synthesize input or enumerate private files.

Native cases include bounded console operation, a Python SIGINT, body/runtime
failure cleanup, monitor enumeration, real Tk startup, registered window close,
deadline, external loop quit, callback/refresh/clear/startup fault injection and
frame smoke. Fault injection combines real API/Tk lifecycle with deliberately
raised fictional errors; it is not proof that Windows naturally failed.
Python SIGINT is not a physical Ctrl+C or forced-window-close test.

The standalone copy passed 16 fresh processes (13 direct CLI and three
instrumented native cases), including optimized commands and a console import
barrier that rejects Tk imports. No source/runtime mutation or bytecode appeared.
Only public source and invented fault details were used.

The dedicated CI matrix runs Python 3.12/3.13 on Windows/Ubuntu. Native test
execution requires `OUTLANDS_AWAKE_NATIVE=1` on Windows; CI refuses native skips.
Ubuntu runs the original 27 plus the 14 new portable cases and explicitly skips
15 native cases. The normal default unittest command does not acquire native
requests or create GUI windows.

Actual idle sleep/display-off, physical Ctrl+C, screen saver/lock/lid/power-button
policy, forced termination, multi-monitor/mixed-DPI behavior across other
layouts, visual quality and extended runtime remain separate manual acceptance.
No result clears unrelated original sources, logs, assets or private records.
