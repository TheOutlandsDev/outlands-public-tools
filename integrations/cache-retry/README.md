# Install and use the cache and retry tools

Start with the [plain-language definitions](../../methodology/CACHE-RETRY.md) and
[machine-readable component guide](components.json). These four independent MIT
Python packages inspect caller-supplied declarations. Each offers a command,
embedded fictional demo and `check(raw_json_bytes)` API. Supply Python 3.12 or 3.13;
the runtime code uses only the standard library.

| Tool | When to use it | Fictional input and result | What the result establishes |
| --- | --- | --- | --- |
| [Cache Key Checker](../../tools/cache-key-contract-checker/README.md) | Review a result's declared namespace, version and input dependencies. | One HVAC job/ruleset entry has the expected key, complete dependencies and one consistent content binding. A game fixture illustrates build metadata. | Declared key derivation and consistent reuse. |
| [Cache Freshness Planner](../../tools/cache-freshness-planner/README.md) | Review a selected result under explicit age and invalidation rules. | created_at=10, lifetime=20 and as_of=20 yield fresh, age=10, expires_at=30. At as_of=40 the fixture is invalidated and expired. | Freshness of the supplied snapshots under the supplied timeline and policy. |
| [Retry Budget Checker](../../tools/retry-budget-checker/README.md) | Review selected attempt records against a stated policy. | One timeout at ordinal 10 with base delay 5 is due at 15; at as_of=20, two of three attempts remain. | Consistency and manual-review eligibility of that declared history. |
| [Idempotency Ledger Reconciler](../../tools/idempotency-ledger-reconciler/README.md) | Compare operation keys, payload fingerprints and result claims. | One unambiguous failed claim passes consistency. Unknown or conflicting claims require review. | Agreement among the supplied claims, including the claimed failed state. |

Every tool's original guide defines the complete schema, row-accounting rules,
refusals and limits. `components.json` names the API, input/result formats,
examples and result fields for human or AI-assisted discovery. Input examples
use opaque invented hashes and identity records rather than real payloads.

## Install independently or as a four-tool group

Download the selected wheel(s), `MANIFEST.json` and `SHA256SUMS.txt` from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/cache-retry-wheels-v1.0.0).
Verify each SHA-256 before installation. One tool needs its own wheel; the collection
needs all five wheels in one directory outside the source checkout. Create a fresh
virtual environment with `py -3.12 -m venv ENV` on Windows or
`python3.12 -m venv ENV` on Ubuntu, then use its Python for one command:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_cache_key_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-cache-retry-collection==1.0.0
```

On Windows PowerShell, substitute `& .\ENV\Scripts\python.exe` for `python`;
on Ubuntu use `./ENV/bin/python`. The environment's `Scripts` or `bin` directory
contains `outlands-cache-key-contract-checker-demo` for an embedded fictional run.
Use `outlands-cache-key-contract-checker --input PRIVATE_JSON` for a selected
private input. Substitute any other individual wheel/command from the component
guide. `outlands-cache-retry` lists the four installed collection commands.
No package-index registration is implied.

## Call a tool from another project

This executable example loads only the wheel's invented fixture and changes its
explicit as-of value. It creates no cache, requests or report files.

```python
import json
from importlib.resources import files
from outlands_cache_freshness_planner.freshness import check
raw = files("outlands_cache_freshness_planner").joinpath("examples", "input.json").read_bytes()
value = json.loads(raw)
value["as_of"] = 40
report = check(json.dumps(value).encode("ascii"))
assert report["status"] == "REVIEW_REQUIRED"
assert report["assessment"]["entries"][0]["state"] == "invalidated"
assert report["assessment"]["entries"][0]["expired"] is True
assert report["cache_mutated"] is False
```

For real use, supply your own complete schema and exact identity bindings. API
refusals raise a fixed diagnostic; the CLI translates them to exit 2. Examine
status, assessment and qualified pins together. Retry state
`ready_for_manual_review` is advisory and `retry_authorized` remains false.
An unknown outcome stays unresolved; it must not be treated as a safe retry.

## Worked methodology and system use case

Run the [installed exercise](exercise.py) with the collection environment's Python.
It checks one invented HVAC cache key, projects its exact dependency bindings into
a freshness review at as_of=40, and reports both invalidation and expiry. It then
uses an explicitly separate operation-key namespace for a fictional refresh
request, checks the retry deadline 15, and reconciles one failed claim against the
same operation snapshot. Unknown-outcome fixtures withhold retry and ledger
qualification. No request is sent, result fetched, cache refreshed or ledger written.

The [Data & Services Stack](../../systems/data-services-stack/README.md) has job
configurations, persistent run history and a fake notification queue, including an
accepted-but-unknown attempt. A future caller-owned adapter could map selected
job/configuration snapshots to dependency fingerprints and selected fake attempt
records to operation, policy and claim contracts. The adapter must define a common
ordinal unit, preserve unknown outcomes, bind exact revisions/hashes, select one
snapshot per semantic slot and declare distinct cache and operation namespaces.
The application's queue states do not automatically equal these tool schemas.
No adapter or live integration is included or qualified here. Actual recipients,
provider details, payloads, job data, journals and reports stay private.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty
absolute output directory outside the repository, then run
`python -B integrations/cache-retry/build_wheels.py --output DIRECTORY` and
`python -B integrations/cache-retry/verify_wheels.py --wheels DIRECTORY`.
The build verifies exact public source manifests and isolates imports into distinct
package names. Fixed synthetic wheel ZIP metadata retains public MIT attribution.
Hosted Windows/Ubuntu Python 3.12/3.13 checks fresh-install each wheel and the
collection, run demos, review fixtures, APIs and this literal documentation example,
and compare all five wheels and both manifest bytes. Public-download checks repeat
after release. These checks establish package behavior on fictional inputs, without
authenticating records, operating a cache or guaranteeing exactly-once execution.
