# Privacy and execution boundary

This publication consists of already public first-party MIT components and fresh
generic application code, contracts, tests and fictional examples. No original
business application, proprietary query/formula/schema, actual record, route,
template, address, credential, provider configuration, operational log or history
is selected. Python/runtime binaries and third-party services are not bundled.

The application reads only explicitly selected configuration/input/workspace
files. Output workspaces, reports and ZIPs must be outside the source installation
and its enclosing Git checkout. Source-check/package commands read trusted package
source named by an explicit manifest. The app does not inventory an environment,
discover credentials, execute selected scripts, scan a data source, contact a host
or send real email. Python imports the trusted application itself. A custom
transport is caller-supplied executable code and is not sandboxed or timed out.

Actual normalized data, forecasts, scores, run hashes/keys, messages, receipts,
configuration and journal history remain private. Raw input bytes and selected
input paths are not stored, but derived results and hashes can still identify
operations. Status omits record content; result/export intentionally return
private data. Validation, fixed errors and source packaging are not anonymizers.

Workspace sessions use an exclusive empty coordination directory. Recovery
requires the operator to assert all other users/processes are stopped. This
assertion is not a process-liveness check. Never make it while another caller is
active. The package is for one synchronous operator on stable trusted local
storage, with unchanged parent directories. It is not a multiuser server, a
hostile-filesystem sandbox or a concurrent/distributed queue. Windows output
permissions inherit parent ACLs; POSIX new files/directories request 0600/0700.

Transport attempts are claimed in persistent state before the callback. Unknown,
invalid or interrupted outcomes do not automatically replay. Only explicit
definite non-acceptance permits retry; an adapter that lies or misclassifies
acceptance can still cause duplicates. A matching delivery report records a
caller assertion, never independent provider evidence. New run keys authorize
distinct runs; semantic deduplication across keys/workspaces/providers is absent.

Writes use the reviewed ordinary-file/native Windows helpers, exclusive creation,
flush and readback verification. Interrupted new output is retained. Hash chains
detect sampled corruption/linkage failures; they are not signatures, access
control or protection against forged histories and rollback to an earlier valid
prefix. Keep an independently trusted head hash if detecting rollback matters.
File flushes and POSIX directory sync do not establish every hardware/power-loss
behavior. Backups, encryption, retention, authorization and provider reconciliation
remain operator responsibilities outside this selected application.

Use invented examples in public issues. Do not upload workspaces, journal files,
raw inputs, exports, receipts, private paths, credentials, provider traces or
screenshots from actual use. No whole-repository history/identity clearance is
implied by this exact-source publication audit.
