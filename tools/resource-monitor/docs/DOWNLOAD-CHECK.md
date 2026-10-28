# Download acceptance — 0.1.1

Run from a fresh extracted focused ZIP with Python 3.12 or 3.13. No pip install,
psutil, actual metrics or external service is needed:

```text
python -B examples/download_check.py --workspace ABSOLUTE_NEW_PRIVATE_DIRECTORY
```

The scratch directory must be new, outside the app, with an existing trusted
local parent. This writes fictional JSON/CSV exports and a fixed-result receipt
there. The private startup URL/token is read only in memory and never printed
by the acceptance check. Retain no real metrics or identifying logs in public.

The check runs the actual Windows/Linux readiness wrapper, starts the Python
demo launcher, checks the HTTP page and token requirement, waits for generated
samples, verifies bounded demo history, downloads and reopens JSON and CSV,
refuses an existing export path, waits for bounded normal shutdown, then restarts
and proves the old token is refused. The prior export bytes remain unchanged.
History is memory-only; restart does not load an export or previous history.

The [download workflow](https://github.com/TheOutlandsDev/outlands-public-tools/actions/workflows/download-handoff.yml)
tests fresh ZIPs on Windows and Ubuntu, compares exact package checksums and
publishes only new releases. Unit/provider/live-sampler and presentation tests
are additional checks with their own stated boundaries.

No browser export, pause/resume rendering or interactive accessibility acceptance
was performed in this release review because Browser access was disabled.
HTTP export checks prove the endpoint and bytes, not the browser download UI.
The portfolio's existing browser adaptation is a separate fictional static demo.
Its new terminal/API walkthrough is an edited sequence of verified receipt
outcomes, not an interface recording. See [full validation](VALIDATION.md).

## Walkthrough sequence

1. Extract → readiness without pip.
2. Start a fictional dashboard on a free loopback port.
3. Token missing → 403; current token → bounded fictional history.
4. Export JSON/CSV → reopen both; existing export preserved.
5. Stop → restart with a new token; old token → 403.
6. Prior export persists; server history intentionally starts fresh.

[Start here](../START-HERE.md) for the user workflow and explicit live-mode options.
