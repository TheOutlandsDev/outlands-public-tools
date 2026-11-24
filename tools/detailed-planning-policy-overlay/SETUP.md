# Offline Detailed Planning Policy Overlay

Use this tool to review how a saved policy changes the lot sizes and uncovered-demand factor in a detailed planning configuration. The CLI reads saved files and prints projected JSON to standard output.

## Verify and install

Compare the downloaded ZIP's SHA-256 with the line in SHA256SUMS.txt. In Windows PowerShell, use the following command.

~~~powershell
Get-FileHash -Algorithm SHA256 .\detailed-planning-policy-overlay-0.1.0.zip
~~~

Use the following command on Ubuntu.

~~~bash
sha256sum -c SHA256SUMS.txt
~~~

Extract the archive. From its top-level directory, create a fresh environment with Python 3.12.16 or 3.15.2. The following commands use the checked interpreter directly on Windows PowerShell.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B planning_overlay.py examples/candidate-policy.json --project-root examples
~~~

Use the following commands on Ubuntu.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B planning_overlay.py examples/candidate-policy.json --project-root examples
~~~

The environment requires Pydantic 2.14.3. The dependency file also pins the exact wheels for the qualified Windows and Ubuntu x64 profiles.

## Supply your own saved inputs

Use [candidate-policy.json](examples/candidate-policy.json) as the overlay policy schema. The policy lists the applicable modality, part number, and lot size for each configured product. It declares the 1.00 recommendation factor and the comparison-only 1.10 factor. It also declares the candidate state and disables production authority.

Keep the detailed configuration at `data/flex_planning/configuration_v1.json` beneath the supplied project root. Supply its reviewed SHA-256 and the reviewed hashes of any additional reconciled inputs using forward-slash relative paths. [Example configuration](examples/data/flex_planning/configuration_v1.json)

The CLI validates every pinned file before parsing the detailed configuration. The projected JSON uses the authoritative lot size and factor for each exact modality and part-number match. It keeps the detailed route, timing, and priority settings and records the policy ID and revision in the configuration and factor provenance. It exits with status 2 and a diagnostic on stderr if validation fails.

The original integration test compares the planner's output using the fictional configuration, orders, and WIP. The recommended start quantities change from `[0, 220]` to `[0, 200]`. The remaining comparison fields match exactly. Release validation records identify the archive hash, runner profiles, dependency pins, and tests.

SHA-256 checks content against the supplied policy. Review policy provenance before using it as an authority, and run the overlay on a stable saved input tree.
