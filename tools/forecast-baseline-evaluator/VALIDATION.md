# Validation and limits

The 38 evaluator methods use fictional series only. They cover all three
methods, fixed-window and repeated-cycle behavior, parameter/type/history limits,
clean-batch refusal, conflicting duplicates, gap/order/series refusal, bounded
containers, point revalidation, finite extreme errors, input preservation,
immutable results, independent metric arithmetic, every evaluation prefix,
future-tail independence, public snapshot equality and actual CLI behavior.
They include file/network/process canaries and fixed interruption diagnostics.

From the repository root:

```text
python -B -W error -m unittest discover -s tools/forecast-baseline-evaluator/tests -v
python -B -W error -m unittest discover -s tools/record-ingestion/tests -v
python -B tools/forecast-baseline-evaluator/demo.py --demo
```

The dedicated Windows/Ubuntu Python 3.12/3.13 workflow runs all 38 evaluator
methods and the 21 original ingestion methods, refusing skips. It runs the
fictional demo and the collection Markdown/JSON check. Before publication,
standalone copies are tested against separately authored generated-case
oracles and exact selected source bytes are privately audited.

These checks establish the documented bounded arithmetic and integration with
the public ingestion contract. They do not validate a private source adapter,
historical forecast, production dataset, business model, empirical usefulness,
forecast intervals, real-world accuracy, delivery service or operational action.
The demo's perfect seasonal score is a property of its invented pattern.
No historical application bodies or operational inputs are needed or selected.
