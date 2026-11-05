# Add model-routing checks to a project

This pilot gives four existing MIT tools individual Python wheel packages and a
four-tool collection wheel. The source implementations remain in `tools/` and the
published Model Routing 4 source ZIP remains unchanged. Wheels built here are a
local pilot until a separately reviewed release publishes them.

Start with [the terms](../../methodology/TERMS.md), then choose the task below.
The [machine-readable guide](components.json) supplies stable IDs, entry points,
input formats, examples and boundaries for an AI assistant or project indexer.

| Task | Tool | Input | Result to inspect |
| --- | --- | --- | --- |
| Check a model catalog's declared limits | [Model Capability Checker](../../tools/model-capability-checker/README.md) | `outlands-model-capability-v1` JSON | `assessment.models`, `models_sha256`, `issues` |
| Check proposed assignments | [Request Routing Checker](../../tools/request-routing-checker/README.md) | `outlands-request-routing-v1` JSON | `assessment.proposals`, `route_plan_sha256`, `issues` |
| Check a proposed fallback order | [Fallback Chain Checker](../../tools/fallback-chain-checker/README.md) | `outlands-fallback-chain-v1` JSON | `assessment`, `plan_sha256`, `issues` |
| Compare declared attempts with that plan | [Inference Receipt Reconciler](../../tools/inference-receipt-reconciler/README.md) | `outlands-inference-receipts-v1` JSON | `assessment`, `issues` |

All four accept exact JSON bytes through `check(raw_json_bytes)` and return a Python
dictionary. They use Python 3.12/3.13 and the standard library at runtime. They
inspect caller-supplied declarations; they do not load models, route requests or
perform inference. Keep real input and report data in a private project directory.

The supplied fictional inputs produce these **selected output fields**. The full
JSON reports also contain counts, pins, explicit false verification flags and
diagnostics. Run the examples to see the complete report.

| Tool | Fictional example result | What the result means |
| --- | --- | --- |
| Model Capability | `PASS`, `consistent_models: 2`, `issues: []` | Two supplied declarations agree with their own limit rules. |
| Request Routing | `PASS`, `eligible_proposals: 1`, `issues: []` | The explicit proposal satisfies the supplied policy and capability declarations. |
| Fallback Chain | `PASS`, `declared_steps: 2`, `maximum_attempts: 2` | The supplied primary-to-reserve order and transition rule are internally eligible. |
| Inference Receipts | `PASS`, `attempts: 2`, `observed_terminal_status: succeeded` | The supplied attempt records reconcile with the declared plan; no actual inference is proved. |

## Install one tool from a local wheel

Build wheels from this checkout into a **new empty directory outside the repo**:

```text
python -B integrations/model-routing/build_wheels.py --output NEW_EMPTY_EXTERNAL_DIRECTORY
```

Create a project virtual environment, then install one wheel from that directory.
For example, from the repository root, substitute your actual wheel path:

```text
python -m venv PROJECT_ENV
PROJECT_ENV/Scripts/python -m pip install --no-index --no-deps NEW_EMPTY_EXTERNAL_DIRECTORY/outlands_model_capability_checker-1.0.0-py3-none-any.whl
PROJECT_ENV/Scripts/outlands-model-capability-checker-demo
PROJECT_ENV/Scripts/outlands-model-capability-checker --input tools/model-capability-checker/examples/input.json
```

On Ubuntu use `PROJECT_ENV/bin/python` and
`PROJECT_ENV/bin/outlands-model-capability-checker`. The filename above is the
expected pure-Python wheel name; use the exact filename in `MANIFEST.json` if the
builder backend chooses a different compatible tag. The fictional input returns
`PASS`. The `-demo` command uses a fictional JSON fixture embedded in the wheel,
so it works without a source checkout. No network access is needed to install
these local wheels.

## Install the four-tool collection

After building all five wheels, install the collection from the same local directory:

```text
PROJECT_ENV/Scripts/python -m pip install --no-index --find-links NEW_EMPTY_EXTERNAL_DIRECTORY outlands-model-routing-collection==1.0.0
PROJECT_ENV/Scripts/outlands-model-routing
```

This resolves four exact-version tool dependencies. It installs commands rather
than a model service or an automatic workflow. The existing [source bundle](../../downloads/model-routing-4/README.md)
is the folder-based alternative: extract it and run each tool's documented `.py`
entry point from its own complete folder. The wheel builder verifies each copied
module against that tool's public source manifest, then changes only package-local
imports so all four can coexist in one Python environment.

## Call one tool from another Python project

After installing the individual wheel:

```python
import json
from outlands_model_capability_checker.models import check

declaration = {"format": "outlands-model-capability-v1", "models": [
    {"id": "hvac-primary", "revision": 1, "tasks": ["classify-ticket"],
     "input_types": ["text"], "output_types": ["label-json"],
     "max_input_units": 600, "max_output_units": 80, "context_units": 700}
]}
report = check(json.dumps(declaration).encode("utf-8"))
assert report["status"] == "PASS"
```

The other imports are
`outlands_request_routing_checker.routes.check`,
`outlands_fallback_chain_checker.fallbacks.check`, and
`outlands_inference_receipt_reconciler.receipts.check`.
Your project must decide what to do with each report. Treat `REVIEW_REQUIRED`
as a review step; a digest or receipt is not proof that inference occurred.

## Where this fits in OUTLANDS systems

The [Corpus & Model Workbench](../../systems/corpus-model-workbench/README.md)
imports reviewed material, prepares exports, and can compare responses from an
explicit loopback model service. These four tools can check a **separate, manually
authored routing plan** before an application uses it and can compare later
caller-supplied attempt records. The Workbench does not currently import these
wheel packages or emit their routing schemas. This is a documented integration
boundary, not a claim of a working adapter. A real adapter would need schema
mapping, private-instance handling, refusal behavior and live tests.

See the [public project map](../../docs/PROJECT-MAP.md) for the other systems.
The intended broader collection will have a component manifest, runtime/dependency
matrix and per-tool install choice; this pilot covers the four Python routing
tools only.
