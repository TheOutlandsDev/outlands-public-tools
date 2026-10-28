# Design and source origins

This standalone first-party MIT application adapts generic control-center methods:
incident candidates, fingerprint-based consolidation, severity and freshness
classification, planned-off/maintenance distinctions, persistent incident review,
and recovery after clean observations. Original implementation sources were read
only; their application, tests, collectors, network probes and service controls were
not executed. Original records and source stay unchanged.

The selected methods are rebuilt around a neutral supplied-observation contract,
fresh private instances and a new CLI/browser application. Identity deliberately
excludes volatile summary text. Missing observations no longer count toward recovery.
New time-weighted coverage arithmetic splits freshness/gap/maintenance intervals;
original host-specific availability collectors and their settings are not selected.

No original runtime snapshots, logs, operational topology, actual signal inventories,
paths, identities, service addresses, credentials, game/server assets, deployment
scripts or third-party packages are included. All public observations, notes,
maintenance windows and review actors are newly invented.

The native guarded I/O files under `reliability/vendor/` are unchanged snapshots
from the public Assessment & Evidence Workbench. `runtime.py` changes only the
instance/schema/example names. HTTP and deterministic source-packaging patterns
adapt that public implementation. The HTTP request backlog is bounded at 32 for
ordinary local browser connection bursts; there are no automatic write retries.
The previous workbench's optional hash-pinned browser-test requirements are reused
unchanged; runtimes, test dependencies and browsers are supplied separately.

First-party source is MIT, copyright TheOutlandsDev. This selected adaptation does
not clear the broader original application family, live configuration or private
records, and does not grant rights to future caller data.
