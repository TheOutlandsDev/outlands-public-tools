# Fictional and live walkthroughs

Run commands from `tools/resource-monitor`. Start with the deterministic stdout
demo or a bounded fictional dashboard:

```text
python -m resource_monitor demo
python -m resource_monitor serve --demo --port 0 --interval .2 --history 120 --duration 120
```

Open the complete printed local URL. Confirm the **FICTIONAL DEMO** badge, CPU
and memory cards, network rates after the second sample, and recent readings.
Use **Pause view**, wait briefly, then **Resume view**. The server continues
sampling while the browser view is paused. JSON/CSV download buttons explicitly
export the server's current retained history.

The browser removes the URL token fragment after connecting. A fresh/reloaded
tab needs the complete current startup URL again or its token in reconnect help.
Stopping the server should show the previous readings as stale/unavailable, not
silently manufacture new zeros.

The tiny [sampling walkthrough](sample_walkthrough.py) prints two deterministic
fictional samples through the actual collector/export code and makes no machine
API or HTTP call:

```text
python -B examples/sample_walkthrough.py
```

For real sampling, install the pinned dependency in a private virtual environment
as documented in the main README, then use `sample --live --count 3 --interval .2`.
To save, explicitly choose a new private output file outside this repository.
Keep actual metrics, timestamps, downloaded exports and capability URLs private.
An empty/new history and first-sample gaps are expected and are not test failures.
