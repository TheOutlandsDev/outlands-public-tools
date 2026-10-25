# Connection Plan Checker review — 2026-10-25

This batch adds [Connection Plan Checker](../tools/connection-plan-checker/README.md),
a fresh Python 3.12+ standard-library implementation of selected connection
planning methods. Original operational launchers, policy installers, collectors,
configuration, endpoints, identities, credentials, records and source mappings
remain private. No original script is copied or executed. The public addition
contains newly authored source, tests, documentation and fictional JSON plans
under the repository MIT license and TheOutlandsDev public attribution.

## Scope and privacy

Plans declare one or more bindings with neutral IDs, `tcp` or `udp`, exactly
`127.0.0.1` or `::1`, and an integer port from 1 through 65535. Exact repeated
transport/address/port tuples form declaration-conflict groups. Protocol and
address families are separate tuples; this does not model runtime socket reuse,
exclusivity, wildcard listeners, dual-stack behavior or platform availability.

Results contain IDs, fixed status/evidence codes, counts and conflict-member
IDs. Addresses, ports, transport fields, input paths and native exception text
are omitted. IDs and relationships can still reveal system design. Real plans
and stdout remain private; this is not anonymization or clearance to publish
operator inputs. The two shipped examples contain only fictional declarations.

The checker reads one explicitly selected bounded control JSON and writes only
to stdout. There is no socket/DNS API, listener/process inspection, target
execution, command generation, rule installation, configuration edit or report
file writer. Plan, runtime, availability and network-probe boundaries are
explicit in the result flags. A conflict-free declaration set does not mean
that any port is free or any connection can work.

Input JSON is limited to 64 KiB and the plan to 128 bindings. Unknown fields,
duplicate JSON keys/IDs, nonstandard constants, unsafe path forms and wrong
types are refused. Input-file metadata and ancestor identities are sampled
before/after a bounded read, with regular-file, single-link and link/reparse
checks. This is not an atomic snapshot or hostile-filesystem sandbox. Use
stable trusted local files. Mapped/mounted storage can involve OS network I/O;
the input-size bound cannot interrupt a blocked filesystem call.

## Validation

Fictional checks cover tuple grouping/order, all members of repeated groups,
protocol/family separation, schema/type/size/count limits, malformed JSON,
input metadata safeguards and preservation, zero socket/process/output-file
activity, fixed error codes and omission of endpoint/path/native-error values.
The local Windows/Python 3.12.7 suite discovered 41 methods: 39 passed and two
native link cases were skipped because those filesystem operations were
unavailable. The API's native-error chaining issue found during review was fixed
and independently retested; formatted errors suppress the selected input path
and native message, while retaining Python source locations.

The integrated root collection run discovered 223 methods: 212 passed and 11
were skipped, with no failures/errors. Fifteen independent fictional CLI
scenarios passed, including both documented examples and schema, JSON, size,
count and path rejection cases. Example hashes stayed unchanged and no listener
was started. Ruff checks/formatting and 149 local document checks passed.
Platform/filesystem skips are not passes.

The dedicated workflow runs on Windows and Ubuntu with Python 3.12/3.13 and
checks documentation/JSON syntax. Its exact commit's Actions results record
the executed platforms. No real host, live port, firewall, connection, service
or production environment is accepted by these offline tests.

Review covers the exact changed public files for this addition. Private deny
lists, source hashes, scanner output, local evidence and publication receipts
are kept outside the repository. This does not re-clear unrelated application
imports, Git history, branches, release assets or unselected drive content.

The 11-file publication set retains four conservative scanner findings in
negative tests: wildcard addresses, a mapped-loopback spelling and a fictional
UNC path, all intentionally refused by the checker. Each finding has a private
file-hash-bound disposition; none contains an operational endpoint or record.
The scanner remains `REVIEW_REQUIRED`, with no rule disabled and zero unresolved
findings after review. There were no private-marker matches or scanner errors.
