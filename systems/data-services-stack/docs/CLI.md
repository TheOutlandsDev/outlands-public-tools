# CLI and complete restart walkthrough

Run from `systems/data-services-stack`, using Python 3.12/3.13. All path tokens
below are placeholders. Substitute explicit absolute private paths outside the
source checkout. Initial workspace/ZIP/report destinations must be new; their
parent directories must already exist. Use `-B` to avoid bytecode caches.

| Command | Behavior |
| --- | --- |
| `init` | Create a new private directory and initial committed empty state |
| `configure --config INPUT_JSON` | Replace configured jobs with a validated neutral document |
| `run --job ID --key KEY --input INPUT_FILE` | Persist one gated data job and its notification intent |
| `status` | Show minimized run/queue summaries and private journal head |
| `result --key KEY` | Return a selected private run, settings, hashes and result |
| `export --key KEY --output NEW_REPORT` | Write that private result through exclusive checked output |
| `dispatch-fake --now TICK --limit COUNT --outcomes TOKENS` | Dispatch only a scripted fictional transport |
| `report-delivery --key KEY --receipt TOKEN` | Record a matching unverified caller delivery assertion |
| `recover --confirm-stopped` | Review unfinished intent after all callers are stopped |
| `demo` | Create a new workspace and run the complete invented restart workflow |
| `source-check` | Verify the source-only manifest; workspace not required |
| `package --output NEW_ZIP` | Build deterministic reviewed-source ZIP; workspace not required |

For workspace commands place `--workspace PRIVATE_WORKSPACE` before the command.
Unknown arguments, including supplied values, are not echoed in parser errors.
Native exception text and selected paths are omitted from error JSON. A rejected
run or fixed operation error exits 2; handled keyboard interruption exits 130.
A successful status command can still show failed/review items; inspect its states.

## Example using source fixtures

```text
python -B stack.py --workspace NEW_PRIVATE_WORKSPACE init
python -B stack.py --workspace PRIVATE_WORKSPACE configure --config examples/jobs.json
python -B stack.py --workspace PRIVATE_WORKSPACE run --job sample --key sample_run --input examples/sample.jsonl
python -B stack.py --workspace PRIVATE_WORKSPACE dispatch-fake --now 0 --outcomes retry
python -B stack.py --workspace PRIVATE_WORKSPACE status
python -B stack.py --workspace PRIVATE_WORKSPACE dispatch-fake --now 1
python -B stack.py --workspace PRIVATE_WORKSPACE report-delivery --key sample_run --receipt fake_receipt
python -B stack.py --workspace PRIVATE_WORKSPACE export --key sample_run --output NEW_PRIVATE_REPORT
```

Each command starts a fresh process, exercising persistent state. The second
dispatch uses a fresh fake, but the outbox still remembers its earlier attempt.
Its acceptance is not real email delivery. The matching report is a caller
assertion. Terminal entries do not resend when dispatch is invoked again.

To inspect an accepted-but-unknown example, start a **different new** demo:

```text
python -B stack.py --workspace DIFFERENT_NEW_PRIVATE_WORKSPACE demo
```

The summary shows blocked bad input, retry across reopen, delivery-reported and
review-required queue states, no replay after another restart, and
`real_delivery_verified: false`. Existing destinations are refused; no private
workspace is overwritten or automatically deleted. The fake script outcomes are
`accept`, `retry`, `reject`, `uncertain`, `accepted_then_unknown`, `interrupt`.
Only a caller's separately reviewed Python adapter could contact a real provider.

Actual configuration/input/result paths and runtime data stay private. Do not
paste real result/export/status output into a public issue or source commit.
