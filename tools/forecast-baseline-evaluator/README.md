# OUTLANDS | Offline Forecast Baseline Evaluator

Explainable last-value, trailing-mean and seasonal-naive forecasts with
prefix-only one-step MAE/RMSE evaluation. Python 3.12/3.13, standard library
only, [MIT licensed](LICENSE).

This is fresh generic reference code, with an unchanged first-party snapshot
of the [public ingestion core](../record-ingestion/README.md). It includes no
historical forecasting implementation, private business rule, formula, query,
source mapping, model asset or record. Common baseline arithmetic is described
in [format and methods](FORMAT.md); the design rationale is in
[architecture](ARCHITECTURE.md).

## Run the fictional example

From the collection root:

```text
python -B tools/forecast-baseline-evaluator/demo.py --demo
```

The `FICTIONAL_FORECAST_DEMO` uses six invented alternating values. Last-value
predicts `[4, 4, 4, 4]`; a two-observation mean predicts `[3, 3, 3, 3]`; a
two-observation season predicts `[2, 4, 2, 4]`. Four one-step holdouts have
MAE/RMSE of 2/2, 1/1 and 0/0 respectively. A conflicting ingestion batch is
refused. This deliberately simple pattern illustrates arithmetic, not evidence
of accuracy on real data. The application reads no operator file or service and
writes no output files. `-B` also prevents interpreter bytecode caches.

## Library use

From this tool directory:

```python
from ingestion import ingest_csv
from evaluator import forecast, rolling_score

clean = ingest_csv("series,period,value\nsample,0,2\nsample,1,4\nsample,2,6")
predicted = forecast(clean, method="mean", window=2, horizon=2)
assert [point.value for point in predicted] == [5, 5]
score = rolling_score(clean, min_history=1, method="last")
assert (score.count, score.mae, score.rmse) == (2, 2, 2)
```

Both functions accept the ingestion `Batch`, call its clean gate, revalidate
typed values and require one contiguous series. They refuse partial/empty
batches, gaps, mixed series, insufficient history and invalid parameters.
`forecast` returns an immutable tuple of `Point`; `rolling_score` returns a
frozen `Score(count, mae, rmse)`. Errors use fixed `ReferenceError` codes.

The included `ingestion.py` is byte-identical to the public source at revision
`be484a9a3b606de1b8a784ced493a6a456c85f52`, SHA-256
`d687e10ea4abb2c6cc35c63294df48ebcc6889b37658217f54e09c95e36b7c4b`.
CI checks equality with the collection copy and runs its 21 original tests.
Use this directory's standard `ingestion` import consistently; independently
loading copies under different module names creates different Python classes.
The snapshot is explicit first-party reuse, not an external package dependency.

See [validation](VALIDATION.md) and [privacy boundaries](SECURITY.md). Real
inputs, forecasts and scores remain private. No model selection, forecast
interval, production acceptance, email delivery or operational action is implied.
