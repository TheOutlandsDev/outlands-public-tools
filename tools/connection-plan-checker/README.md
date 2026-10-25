# Connection Plan Checker

Validate an explicitly selected JSON plan of loopback listener claims and find
repeated declarations. Python 3.12+, standard library only. The checker reads
the selected plan and writes JSON to stdout. It does not open sockets, resolve
DNS, inspect running processes, execute programs, generate commands, install
rules, change configuration or create report files.

This is a declaration check. A result without declared conflicts does not prove
that a port is available, a listener can start, a connection works, or a runtime
configuration is safe. No runtime or availability check is performed.

## Fictional examples

Run from the collection root:

```text
python -B tools/connection-plan-checker/connection_check.py --plan tools/connection-plan-checker/examples/distinct-plan.json
```

Expected exit: **0**, `NO_DECLARED_CONFLICTS`, with four `DISTINCT` checks,
zero conflict groups and zero conflicting bindings. The example keeps TCP and
UDP claims separate and treats the two accepted address spellings separately.
That models declaration equality, not operating-system behavior.

```text
python -B tools/connection-plan-checker/connection_check.py --plan tools/connection-plan-checker/examples/conflicting-plan.json
```

Expected exit: **1**, `DECLARED_CONFLICTS`, with five bindings, two conflict
groups and four conflicting bindings. The groups contain `sample_a` with
`sample_c`, then `sample_b` with `sample_d`; `sample_e` remains `DISTINCT`.
Both files are newly authored fictional inputs. No program needs to listen on
their sample ports, and neither command starts one.

## Plan format

The UTF-8 JSON object has exactly `schema_version` and `bindings`:

```json
{
  "schema_version": 1,
  "bindings": [
    {"id": "sample_a", "transport": "tcp", "address": "127.0.0.1", "port": 49152}
  ]
}
```

A plan contains 1 to 128 bindings. Each binding has exactly the four fields
shown above:

| Field | Accepted value |
| --- | --- |
| `id` | A lowercase ASCII letter, then lowercase letters, digits, underscores or hyphens; at most 40 characters total; unique in the plan |
| `transport` | Exactly `tcp` or `udp` |
| `address` | Exactly `127.0.0.1` or `::1` |
| `port` | A JSON integer from 1 through 65535; booleans, strings and floating-point numbers are refused |

The schema version must be the integer `1`. Unknown fields, duplicate JSON
keys, duplicate IDs, nonstandard JSON constants and wrong types are refused.
Address aliases, hostnames, wildcard addresses, other local addresses, remote
endpoints, whitespace variants and address ranges are outside the schema.
There are no connection, identity, process, command or installation fields.

## Conflict and result semantics

Two bindings conflict in this plan exactly when their transport, address and
port values all match. Every member of a repeated tuple is `CONFLICT`, including
repeated UDP claims. This is an intentional declaration rule; it does not model
socket reuse, exclusivity or platform bind rules. TCP and UDP are distinct
tuples, and the two loopback address spellings remain distinct. No dual-stack
or cross-family compatibility is inferred.

Results include per-check IDs, `DISTINCT` or `CONFLICT`, and the fixed evidence
codes `UNIQUE_DECLARED_BINDING` or `REPEATED_DECLARED_BINDING`. Conflict groups
contain only their member IDs. Checks follow declaration order; groups follow
the first appearance of their tuple, with member IDs in declaration order.
Results omit the binding transport, address and port fields, input paths and
native exception text.

The result scope is `DECLARED_LOOPBACK_BINDINGS_ONLY`, with fixed flags
`network_probed: false`, `programs_executed: false`, `runtime_verified: false`
and `availability_verified: false`. Counts report the number of bindings,
conflict groups and conflicting bindings. Exit `0` means
`NO_DECLARED_CONFLICTS`, exit `1` means `DECLARED_CONFLICTS`, and exit `2` means
`ERROR` with a fixed code. None grants runtime acceptance.

Unobserved factors include existing listeners, wildcard sockets, platform
dual-stack behavior, reuse options, access restrictions and changing runtime
state. Distinct declarations can still fail when used by a real application.

## Privacy and filesystem limits

IDs and conflict relationships are echoed. They can disclose a project or its
design even when addresses and ports are omitted. Choose neutral IDs and keep
real plans and stdout private. Schema validation is not anonymization, a secret
scan, an IP review or approval to publish operator inputs. The shipped examples
are fictional; avoid replacing them with real configurations in the checkout.
Use a separate location following the
[private workspace guide](../../docs/PRIVATE-WORKSPACE.md) for your own plans.

Only the explicitly selected input is read, limited to 64 KiB. It must be a
regular file with one link, with verifiable file and ancestor identities.
Selected paths are limited to 4,096 characters and 64 parts; parent traversal,
UNC paths, drive-relative paths and unsafe stream/device forms are refused.
Symlink/reparse paths, special nodes and detected type or identity changes are
refused. These checks do not freeze a tree or
create a hostile-filesystem sandbox. Use stable trusted local storage. No
socket or DNS API is used, but reading files on mapped drives or mounted shares
can still involve the operating system's network storage stack. Remote-storage
classification, arbitrary mounts and concurrent writers are not proven safe.
A blocked filesystem operation cannot be interrupted by the input size limit.

The CLI supports `--plan FILE`, `--help` and `--version`. It has no report-file
option or output-directory mode. Python is invoked with `-B` in the examples to
avoid generating bytecode files during these commands.

## Provenance, licensing and validation

This is a fresh neutral implementation of selected owner-reported planning
methods. Original operational scripts, configurations, source mappings, keys,
credentials, identities, private endpoints and captured records are excluded.
No original private launcher, policy installer or diagnostic collector is
copied or executed.

Selected original source and fictional examples use the repository's
[MIT license](../../LICENSE), attributed to TheOutlandsDev. That grant does not
relicense operator inputs or third-party material. The owner's personal-work
statement and fresh implementation do not independently prove ownership of all
historical material. See the
[batch review](../../docs/BATCH-9-CONNECTION-PLAN.md) for actual validation results
and platform limits. CI covers Python 3.12 and 3.13 on Windows and Ubuntu;
passing offline tests never proves runtime listener behavior.
