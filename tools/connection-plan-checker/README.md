# Connection Plan Checker

Validate an explicitly selected JSON plan of loopback listener claims and find
repeated declarations. Python 3.12+, standard library only. The checker reads
the selected plan and writes JSON to stdout. It does not open sockets, resolve
DNS, inspect running processes, execute programs, generate commands, install
rules, change configuration or create report files.

## Standalone source release 0.1.0

Download the reviewed source ZIP from
[connection-plan-checker-v0.1.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/connection-plan-checker-v0.1.0).
The ZIP contains source, tests, fictional examples and the full [MIT license](LICENSE).
Supply Python separately; no installer, pip distribution, interpreter,
runtime/dependency binary, actual plan/result, private source or raw log is
bundled. The CLI needs only `connection_check.py` and Python's standard library,
without a sibling tool, donor, network, model or account.

Fresh standalone qualification selects Windows/Ubuntu with Python **3.12, 3.13,
3.14 and 3.15.2**, in new no-pip environments with zero installed distributions.
It selects all **41 original methods/103 assertion calls**, nine required
helper ASTs and 26 copied single-script CLI methods: **67 per lane, 536 across
eight lanes**. Selected counts are not passing results; actual versions,
outcomes and named skips belong to release `VALIDATION.json`. Historical
collection evidence below is separate. Runtime and both original JSON controls
retain exact baseline Git bytes, with no new tuple, output or input-path repair.

Use [USAGE.md](USAGE.md) for complete fictional JSON/exit outcomes with retained
input/prior-capture bytes. See [qualification](docs/QUALIFICATION.md),
[private workspace](docs/PRIVATE-WORKSPACE.md) and
[provenance](docs/PROVENANCE.md). Keep actual plans/captures outside source.

The standalone original-method adapter is selected explicitly:

```text
python -B -m unittest discover -s tests -p test_original_connection.py -v
```

Only an original ROOT-relative subprocess test needs an owned temporary runtime
mirror. It copies the actual extracted script into its fixture hierarchy and
verifies exact hashes before/after. In-process tests load the actual extracted
checker; copied CLI consumers use one copied script. No duplicate runtime or
unrelated application is shipped. See qualification for this test-only boundary.

This is a declaration check. A result without declared conflicts does not prove
that a port is available, a listener can start, a connection works, or a runtime
configuration is safe. No runtime or availability check is performed.

## Fictional examples

Run from the extracted module directory:

```text
python -B connection_check.py --plan examples/distinct-plan.json
```

Expected exit: **0**, `NO_DECLARED_CONFLICTS`, with four `DISTINCT` checks,
zero conflict groups and zero conflicting bindings. The example keeps TCP and
UDP claims separate and treats the two accepted address spellings separately.
That models declaration equality, not operating-system behavior.

```text
python -B connection_check.py --plan examples/conflicting-plan.json
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
`ERROR` with a fixed code. Exit `130` means interrupted. None grants runtime acceptance.

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
[private workspace guide](docs/PRIVATE-WORKSPACE.md) for your own plans.

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

Path-component checks apply **after absolute-path normalization**. There is no
original-spelling precheck before that normalization. Actual fictional Windows
probes on Python 3.12.7/3.15.2 accepted canonical spelling, leaf trailing dot,
leaf trailing space and parent trailing dot with exit 0/`NO_DECLARED_CONFLICTS`;
parent trailing space returned exit 2/`INPUT_PATH_INVALID`. Input/runtime bytes
were preserved. Use fully spelled canonical trusted paths. These mixed measured
normalization observations do not establish universal alias safety or blanket
original-component refusal.

The CLI supports `--plan FILE`, `--help` and `--version`. It has no report-file
option or output-directory mode. Python is invoked with `-B` in the examples to
avoid generating bytecode files during these commands.

## Provenance, licensing and historical validation

This is a fresh neutral implementation of selected owner-reported planning
methods. Original operational scripts, configurations, source mappings, keys,
credentials, identities, private endpoints and captured records are excluded.
No original private launcher, policy installer or diagnostic collector is
copied or executed.

Selected original source and fictional examples use the repository's
[MIT license](LICENSE), attributed to TheOutlandsDev. That grant does not
relicense operator inputs or third-party material. The owner's personal-work
statement and fresh implementation do not independently prove ownership of all
historical material. See the
[batch review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-9-CONNECTION-PLAN.md)
for historical results and platform limits. The original local Windows/Python
3.12.7 suite discovered 41 methods: 39 passed/two unavailable native-link skips.
Its integrated collection and 15 separate fictional CLI scenarios are historical
evidence; skips are not passes. Historical dedicated CI selects Python 3.12/3.13
on Windows/Ubuntu. Fresh standalone versions/counts/outcomes are recorded
separately in release validation. Passing offline tests never proves listener
behavior. Standalone preparation used AI assistance without exclusive-authorship
claims; see [provenance](docs/PROVENANCE.md) and
[third-party notices](THIRD-PARTY-NOTICES.md).
