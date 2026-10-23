# OUTLANDS | Keep Awake source review

This selected source addition contains the Windows utility, usage documentation and synthetic tests. It includes no runtime captures, private source ledger, original history, configuration, user data, installer or dependency implementation. Licensing remains unassigned.

## Staged corrections

Default argparse diagnostics could echo supplied values and derive help/version output from a local script path. They now use fixed-code failures and a static name. Huge finite minute values that overflowed during seconds conversion are rejected. Non-Windows runtime/self-test commands stop before native calls, while help/version remain available.

Tk root lifetime is protected by a finally boundary, including startup failures and mainloop exit; handled Tcl errors no longer echo their native detail. A failed keep-awake clear call remains visible through a warning/local active flag and a failure status, without claiming successful power restoration. The visual design, original application identifier/version, compatibility options and normal power-request flags remain retained source context. The private GitHub repository was not edited.

## Evidence and limits

Fresh isolated Python 3.12.7/Linux tests: **27 passed, zero failures/errors/skips**. Baseline comparison: 15 passed, 7 failed, 5 errored; the twelve demonstrated issues are corrected. Tests cover helpers, parser/privacy/durations, platform guard, simulated flags and cleanup, fake clock and fake Tk lifecycle. No DLL, Windows power/display/monitor call, real GUI, native self-test/smoke-test command or power setting was exercised. Resource-bounded child execution used fail-closed network syscall denial and a blocked-socket selfcheck. Code/test bytes were stable.

The test count is synthetic Python behavior evidence, not Windows acceptance or UI/performance proof. Windows API, Tk rendering, mixed-DPI/multi-monitor geometry and actual power-policy/restore behavior remain unvalidated. The animation is deterministic and performs no AI inference. Fullscreen is not a locked session.

The [Microsoft API reference](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate) was reviewed to interpret flags and limits; it is not evidence that this binding was run successfully. The [tool README](../tools/keep-awake/README.md) distinguishes information commands from opt-in native tests and documents stopping, compatibility flags and cleanup limits.

## Provenance

The owner reports personal creation with AI assistance. The retained sanitized source packet and prior publication manifest verify, with historical original/staged hashes and a recorded earlier cleanup-message adaptation. The original selected drive path could not be read, and a bounded name-only discovery returned a drive I/O error. A fresh original-file equality check is **unverified**; no deletion or relocation conclusion is made. The candidate is based on retained verified source, not a rediscovered original or new ownership finding. AI-assisted changes are disclosed; no required notice was removed.

No open-source license is assigned; see [LICENSING.md](../LICENSING.md). This review covers only the selected script/docs/tests, not other folders or a production-ready release.
