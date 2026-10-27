# Contracts and baseline methods

Both APIs require a clean public ingestion `Batch`: a tuple of 1–256 `Point`
records, an empty issues tuple and a nonnegative integer duplicate count.
Record, issue and duplicate counts together cannot exceed 256. Identical
duplicates are permitted; conflicting or otherwise rejected records block use.
The evaluator requires the actual `Batch`/`Point` classes from its standard
`ingestion` import and revalidates every point's fields.

Each point uses the public ingestion domain: a canonical ASCII series token,
an integer ordinal `period` from 0 through 1,000,000 and a finite numeric value
from -1,000,000,000 through 1,000,000,000. All records must have the same series
and strictly consecutive periods in increasing order. No sorting, gap filling,
business calendar, unit conversion or date inference is performed.

## Forecast

`forecast(batch, horizon=1, method="last", window=3, season=1)` uses:

| Method | Prediction | Required history |
| --- | --- | --- |
| `last` | Repeat the last observed value for every future period | One observation |
| `mean` | Arithmetic mean of the last `window` observed values, held fixed for the whole horizon | At least `window` observations |
| `seasonal` | Repeat the last `season` observed values, starting at the oldest value of that final cycle | At least `season` observations |

`horizon` is an exact integer from 1–32; `window` and `season` are exact integers
from 1–256. Booleans and floating/string parameters are refused. All parameters
are validated even when the selected method does not use them. Methods are
exact case-sensitive strings. Future periods must remain at or below 1,000,000.
Forecasts do not feed predicted values back into a moving window or fit a model.

## Evaluation

`rolling_score(batch, min_history=3, method="last", window=3, season=1)` predicts
each observation after the initial prefix from only its earlier observations.
For holdout index `i`, the predictor receives `records[:i]`, never the holdout or
later values. The prefix grows after each observation. The target is always
one period ahead; this is not a multi-horizon backtest or a fixed-origin split.

`min_history` is an exact integer from 1–256, must leave at least one holdout,
and must satisfy the selected method's required history. It is never silently
increased. Each holdout contributes equally, with `error = predicted - actual`:

- MAE = sum of absolute errors / holdout count.
- RMSE = square root of (sum of squared errors / holdout count).

The implementation uses `math.fsum` and finite bounded float arithmetic. Scores
are not rounded, clipped, percentage-normalized, confidence intervals or proof
of business suitability. Different minimum histories produce different holdout
sets; compare methods only on intentionally matched evaluation settings.

## Refusals and bounds

The ingestion clean gate raises `BATCH_REVIEW_REQUIRED`. Evaluator refusals use
`FORECAST_BATCH_INVALID`, `FORECAST_POINT_INVALID`, `FORECAST_ORDER_OR_GAP`,
`FORECAST_METHOD_INVALID`, `FORECAST_PARAMETER_INVALID`,
`FORECAST_HISTORY_REQUIRED`, `FORECAST_PERIOD_LIMIT` or
`EVALUATION_HISTORY_REQUIRED`. Revalidated fields retain ingestion's fixed
field-error codes. Payloads, parameter values and native exception text are not
included in these errors. A trusted Python caller can construct or deliberately
mutate objects; these checks are not isolation from hostile application code.

In-memory bounds limit normal work to 256 records and 32 forecast points or
255 one-step evaluations. They are not hard process CPU/memory quotas.
