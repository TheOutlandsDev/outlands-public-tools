# Focused application handoff

The Toolkit snapshot stays immutable. These separate focused releases add a
short first-run path for two applications:

| Application | Focused source ZIP | First result | Recovery checked |
| --- | --- | --- | --- |
| [Local Site Builder](../tools/local-site-builder/START-HERE.md) | 1.0.2 | Private draft, explicit local publish | Restart, offline verified backup, corruption refusal, fresh restore |
| [Resource Monitor](../tools/resource-monitor/START-HERE.md) | 0.1.1 | Bounded fictional resource history | Reopen explicit JSON/CSV, preserve existing export, new token after restart |

Only reviewed committed app source, licenses/notices, original fictional
examples, tests and documentation are packaged. Node/Python, npm dependencies,
native libraries, optional psutil, credentials, databases, exports and logs are
not included. Each app's source gate has an explicit allowlist and SHA-256 manifest.

From a clean committed collection checkout, select **new absolute directories
outside the checkout** with existing trusted local parents:

```text
python -B downloads/build.py --output ABSOLUTE_NEW_PACKAGE_DIRECTORY
python -B downloads/accept.py --packages ABSOLUTE_PACKAGE_DIRECTORY --workspace ABSOLUTE_NEW_PRIVATE_DIRECTORY
```

The second command deliberately installs the locked Site Builder dependencies
into its disposable extracted app. It runs tests plus the complete synthetic
HTTP/CLI handoff. It creates a private random `.env` there and private synthetic
sites/exports beside that app. Keep the scratch tree out of GitHub. It never
targets an existing configured app; existing output/workspace paths are refused.

The builder uses raw Git blobs, stable member ordering/timestamps and stored ZIP
members. An uncommitted change to either app is refused. Every manifest member
is checked again before extraction and application execution. Windows and Ubuntu
run independently and compare all package/checksum bytes before publication.
`publish.py` runs only in this repository's main CI, creates new named versions
and retains existing releases without replacement. No runtime credentials or
long-lived GitHub token are embedded in source or packages.

These checks establish a fresh application/dependency install on available hosts
and CI runners. They do not establish a clean operating-system install, a new
local visual check, mobile editing, calibrated telemetry or public backend hosting.
The portfolio's new terminal/API walkthrough is an explanatory replay of fixed
receipt outcomes; earlier actual interface captures remain separately labeled.

The [shared catalog](../catalog/README.md) records the newer focused versions
alongside the unchanged Toolkit snapshot. Its generated directory links each
focused download, quick start, demo and methodology; Site publication remains
an explicit supported workflow.
