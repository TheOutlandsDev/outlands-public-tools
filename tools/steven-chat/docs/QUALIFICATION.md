# Qualification contract — Steven Chat 1.0.0

This record defines release gates. Accepted release `VALIDATION.json` records
actual results for its reviewed commit; required selections are not assumed
passes. The preserved [0.1.0 historical record](VALIDATION.md) is earlier evidence,
and the unchanged package runtime already identifies itself as 1.0.0.

## Source and interpreter identity

The source ZIP contains 36 allowlisted source files plus `SOURCE-MANIFEST.json`,
37 members. It includes seven unchanged runtime files, original tests and their
fictional HTTP fixture, a static fictional session, current/retained docs and
qualification helpers. No interpreter, Ollama implementation, model weight,
environment, actual conversation, server installation or raw log is included.
Hashes/build manifest bind selected bytes; unsigned hashes are consistency checks.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 using the
20261110 standalone archive recipe for Windows/Ubuntu. Preparation checks archive
SHA-256, actual interpreter version/executable hash and a fresh environment with
no installed Python distributions. It does not require a global install/admin,
install pip in the application, or establish independently reproducible Python.

## Original and copied-runtime checks

Eight lanes select 75 unchanged originals (17 CLI, 31 client, 27 session tests)
plus 30 copied-runtime checks each: 105 selections per lane, 840 total, comprising
600 original and 240 copied selections. The originals contain 137 assertion calls
within tests, six helpers, twenty top-level runtime definitions and two HTTP
fixture definitions. Selection counts differ from assertion counts. Original
runtime, tests, fixture and five historical records stay byte-identical.

Actual passes, named platform skips, failures and errors remain separate. Skip
policy IDs must be selected and unique. Opposite-platform filesystem cases may
skip by exact policy; a local symlink privilege skip requires the actual Windows
1314 error. Hosted strict mode permits no privilege skip. Hardlink checks execute.
No fixed pass/skip total is assumed across hosts.

Checks cover explicit connection opt-in, canonical loopback endpoints, disabled
proxy/redirect behavior, model names, strict bounded JSON, request/response shapes,
whole-pair context handling, complete sessions, fresh output, native path cases,
interactive recovery, terminal escaping and entry-point identity. Package exports,
CLI aliases and copied runtime bind actual source files. Bounded loopback HTTP
fixtures run and the offline demo is checked; no actual Ollama/model is involved.

## Exact independent fictional guide

The [guide](../USAGE.md) executes its exact published block in fresh no-pip 3.15.2
with seven copied runtime files. Its authored bounded loopback fixture and exact
request/session expectations import no client logic or original fixture. Working
proof is preserved separately from one committed-head rerun. Twenty-five source
hashes include the actual qualifier and all five retained records.

Thirty-eight guide cases check four offline demo/alias executions, eighteen
selected HTTP requests (one GET/seventeen POSTs), six fresh saved sessions and
six immutable fixture inputs. Exact request headers/JSON and full histories are
compared; code-like replies remain data. Seventeen refusals are before HTTP and
eight after it. Thirteen payload hashes and one manifest readback bind fourteen
workspace files. Refused existing saves/missing parents may follow a completed
request and printed answer; the guide explicitly records that ordering.

Positive scope fields `offline_demo_checked` and `loopback_fixture_used` are true.
All eight exclusion fields remain false: actual Ollama used, real model inference
verified, model quality verified, GPU compatibility verified, backend cloud
isolation verified, models downloaded, Ollama servers installed/started and real
conversations used. A loopback address/non-cloud label cannot attest a backend's
own routing, privacy, liveness, model availability or rights. No cloud service,
generated tool/code execution, real transcript or device integration is tested.

## Filesystem, privacy and evidence limits

Fresh session creation uses exclusive open and refuses linked paths/parents
where supported; it is not a transaction. The client accepts relative paths and
does not provide a general UNC/alternate-stream/absolute-only policy. Bounded
regular input reads are not atomic stable snapshots against concurrent mutation.
Path checks have race limitations; failed writes may leave partial fresh files.
Flush/fsync does not establish rollback or cross-platform durability. Socket
timeouts are not hard whole-process deadlines or backend cancellation guarantees.

Prompts/replies are plaintext. Terminal escaping is separate from stored text;
it does not anonymize, encrypt, erase or limit backend/OS logs. POSIX mode 0600
does not harden inherited Windows ACLs. No defaults endorse a model or prove
quality, safety, performance, memory requirements, licenses or hardware support.
Public validation retains sanitized counts/versions/byte identities, excluding
actual machine paths, raw logs, ephemeral endpoints and real conversations.

Use the [Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
only in new owned external workspaces. Review actual release workflow results.
