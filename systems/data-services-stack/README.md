# OUTLANDS | Generic Data & Services Stack

A complete local Python application for configurable data jobs: bounded CSV/JSONL
ingestion, baseline forecasting/evaluation, persistent run history, a persisted
notification queue, restart review, CLI and deterministic source packaging.
Python **3.12 or 3.13**, standard library only, [MIT licensed](LICENSE).

The package consolidates the reviewed public components behind one ingestion
type system. New orchestration and storage use fresh neutral contracts. No
historical application code, business query/formula/schema, original mapping,
actual recipient, provider setting, credential or operational record is included.
Only a fake transport is supplied. Real provider adapters are caller-owned work.

## Run the complete fictional walkthrough

From the collection root:

```text
cd systems/data-services-stack
python -B stack.py --workspace NEW_PRIVATE_WORKSPACE demo
```

Replace `NEW_PRIVATE_WORKSPACE` with a **new absolute directory outside the
source checkout**, under an existing private parent. It is a placeholder, not a
directory to create inside this package. Existing directories are refused.

The demo actually creates private persistent state. It configures a job, accepts
six invented records, predicts three values of 10, evaluates three holdouts
(MAE/RMSE both 4), blocks invalid input, schedules a safe fake retry, closes and
reopens, records acceptance and a matching caller delivery report, then retains
an accepted-but-unknown fake attempt for review across another restart. It sends
no real email. The JSON summary identifies `FICTIONAL_DATA_SERVICES_DEMO` and
`real_delivery_verified: false`.

## Use an empty workspace

Keep replacing the same workspace placeholder with your selected absolute path:

```text
python -B stack.py --workspace NEW_PRIVATE_WORKSPACE init
python -B stack.py --workspace PRIVATE_WORKSPACE configure --config examples/jobs.json
python -B stack.py --workspace PRIVATE_WORKSPACE run --job sample --key sample_run --input examples/sample.jsonl
python -B stack.py --workspace PRIVATE_WORKSPACE status
python -B stack.py --workspace PRIVATE_WORKSPACE result --key sample_run
python -B stack.py --workspace PRIVATE_WORKSPACE dispatch-fake --now 0 --outcomes retry
python -B stack.py --workspace PRIVATE_WORKSPACE dispatch-fake --now 1
```

`--workspace` precedes the command. Source examples are fictional; actual input,
configuration, results and runtime state stay private. `status` omits records,
message bodies, routes and receipts. `result` and `export` explicitly expose
private run data to their caller. See the complete [CLI walkthrough](docs/CLI.md).

## Included application boundaries

| Layer | Included behavior |
| --- | --- |
| Shared components | Public ingestion core, three baseline methods, prefix-only MAE/RMSE and explicit outbox outcomes |
| Job configuration | Strict versioned JSON, up to 16 named jobs; no source paths or credentials in the schema |
| Orchestration | Clean-batch gate, persistent run keys, blocked/error records and result/notification atomic visibility |
| Persistence | Immutable verified snapshots, chained hashes and separate empty commit markers; no selected schema/code execution |
| Queue | Durable claims before transport callbacks, bounded retries, matching caller delivery assertions and uncertainty without replay |
| Recovery | Explicit stopped assertion, interrupted output retained, unfinished runs/attempts moved to review |
| CLI and packaging | Explicit paths, checked I/O, exclusive exports, deterministic source-only ZIP and source manifest |

There is no database server, web service, autonomous scheduler or included SMTP
client. Each CLI invocation performs one bounded operation. A trusted Python
caller can supply its own synchronous transport through the documented API.
There is no exactly-once guarantee, provider verification, automatic replay of
unknown attempts or atomic power-loss guarantee. Existing receipt/key identity
is scoped to the retained workspace. See [persistence and recovery](docs/PERSISTENCE.md).

## Documentation and source checks

- [Configuration and API](docs/CONTRACTS.md)
- [Architecture and decisions](docs/ARCHITECTURE.md)
- [CLI and restart walkthrough](docs/CLI.md)
- [Persistence, limits and recovery](docs/PERSISTENCE.md)
- [Validation and platform boundaries](docs/VALIDATION.md)
- [Public component provenance](docs/COMPONENTS.md)
- [Privacy and execution boundary](SECURITY.md)
- [Source packaging](docs/RELEASE.md)

```text
python -B run_checks.py
python -B stack.py source-check
python -B stack.py package --output NEW_PRIVATE_SOURCE_ZIP
```

The last output must also be outside the source checkout and must not exist.
It contains only manifest-selected source, tests, documentation and fictional
examples. Keep actual workspaces, generated reports, input files and provider
integrations outside publication. Runtime validation does not anonymize data.
