# Validation and evidence limits

Run from the module folder with CPython 3.12 or newer:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Tests use invented observation sequences and disposable files. CLI tests run
actual child processes, including optimized Python refusal guards. Model tests
cover unknown gaps, initial absence, repeated states, exact-ID comparison,
strict replay, limits, export validation and omission of identifying fields.
Actual disposable child-process tests exercise successful bounded reads,
oversized output, timeout, cancellation and suppression of private stderr.

Native withdrawn Tk tests exercise idle startup, fictional demos, explicit scan,
explicit entry selection, parameter refusal, async worker updates, Stop, private
ID details and explicit fresh-report save. One worker workflow uses the actual
monitoring model with a generated query provider; this is not live hardware
acceptance. Test windows remain hidden and no real camera/audio stream is opened.

Require native Tk rather than allowing a missing-display skip:

```powershell
$env:USB_MONITOR_REQUIRE_TK = '1'
python -B -W error -m unittest discover -s tests -v
```

Linux with Tk and an X virtual framebuffer:

```sh
USB_MONITOR_REQUIRE_TK=1 xvfb-run -a python3 -B -W error -m unittest discover -s tests -v
```

Windows qualification can explicitly enable one read-only native enumeration:

```powershell
$env:USB_MONITOR_REQUIRE_NATIVE_QUERY = '1'
python -B -W error -m unittest discover -s tests -v
```

That test queries present USB PnP entries and validates the adapter output. It
prints no device IDs/names and changes no device settings. Its acceptance can be
an empty list on a VM; it does not prove access to a particular physical device.
Cold CIM startup can hit the unchanged five-second query deadline. Native
qualification permits at most three calls when earlier calls time out, reports
the attempt/timeout counts, and still requires one complete validated native
query. Persistent timeout or any other query error fails the test. A timeout is
not counted as a successful observation or hidden as a skip.
Without this explicit flag, that native collection test is skipped. Configured
CI sets the flag on Windows only and requires Tk on Windows/Ubuntu. Linux native
enumeration is intentionally refused. Workflow configuration alone is not proof
that jobs passed; see Actions and the collection review for observed results.

A local read-only Windows enumeration passed during development. A restricted
execution sandbox denied CIM access; the same authored query passed in the
normal local user context. That environment distinction is not a device failure
and does not mean the application repairs or bypasses access controls. No raw
device list or native error log is in this source package.

No controlled physical unplug/replug, port relocation, sleep/resume, long-term
monitoring, camera streaming, microphone capture, ETW capture, device reset,
driver installation or power-setting change was performed for publication.
These remain separate user-visible acceptance scenarios. Polling does not prove
electrical state, complete event coverage, causal diagnosis or physical identity.
Skips are reported separately from passes. Test totals include repeated
first-party helper checks and are not a count of product features.
