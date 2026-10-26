# Keep Awake native Windows review

This batch hardens only the existing public MIT Keep Awake script and adds
invented failure fixtures, native tests, CI and documentation. It includes no
original private application, configuration, user record, credential, endpoint,
runtime capture, monitor layout, DLL, font or third-party implementation.
The public identity remains TheOutlandsDev and upstream notices remain intact.

## Corrections

Handled runtime/self-test errors and restoration warnings now use fixed
categories without native exception values. Unknown runtime details become
`RUNTIME_FAILED`; the binding does not interpret unspecified last-error values.
Requests reject refresh/clear calls from a different creating Python thread.
The existing continuous/system/display flags and normal CLI options remain.

Tk callback exceptions previously could print a traceback while leaving the
main command successful. A callback reporter now closes the app and returns
failure. Periodic power errors also close without a blocking details dialog.
App cleanup runs after an early mainloop quit, canceling its timer before root
destruction. A GUI clear failure remains a failure even if later context cleanup
succeeds. Self-test and UI smoke checks and transitions survive `python -O`.

The original 27 tests remain; one fake app explicitly supplies `failure_code`
and `close`. The original helpers, animation/scene/event geometry methods,
parser options and non-Windows platform rejection are retained. No dependency
or private input is added. The original source-readback/provenance gap remains;
this work uses public source and makes no new original-drive ownership claim.

## Validation boundary

Local Windows/Python 3.12.7 and Tk 8.6: **56 methods passed**, no errors, failures
or skips. That is the original 27 synthetic tests plus 14 new portable checks
and 15 opt-in native Windows cases. The native cases use real power calls and
Tk, with labeled fictional fault injection. Independent calls observe expected
previous thread flags after acquire/clear; they do not observe physical sleep.

A separate single-file package passed **16 fresh processes**: 13 direct CLI
invocations and three instrumented native cases. Normal and optimized console,
self-test and UI smoke commands passed; a console Tk-import barrier, Python
SIGINT cleanup and callback-failure process also passed. The source/runtime
bytes stayed unchanged; no bytecode was produced. Captures remain private.

CI runs the original and new suites separately on Windows/Ubuntu Python
3.12/3.13. Windows native cases are required without skips. Linux keeps its
platform rejection and runs portable fixtures; 15 native cases are explicitly
skipped. Exact-commit results, selected-byte hashes and scanner dispositions
are recorded separately. The unchanged public detectors and private markers
review only the selected publication files; that is not clearance of all
repository history or held sources.

## Remaining limits

Read the [Windows contract](../tools/keep-awake/docs/WINDOWS.md) and
[usage](../tools/keep-awake/README.md). Native success is request/Tk lifecycle
evidence, not actual idle sleep, physical Ctrl+C, screen saver, lock, lid/power
button, mixed-DPI/other-layout, visual-quality, long-runtime or forced-exit proof.
The application is standalone; per-thread flags are not independent nested
request handles. Runtime captures can identify a machine and remain private.
No power plan is edited and no release asset or unrelated held rights family
is changed by this source addition.
