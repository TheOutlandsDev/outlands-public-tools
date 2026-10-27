# Offline Forecast Baseline Evaluator

This selected batch adds fresh neutral last-value, observed trailing-mean and
seasonal-naive forecasting, plus prefix-only one-step MAE/RMSE evaluation. It
includes a fictional demo, authored design/format/privacy notes and tests.
An unchanged copy of the already public MIT ingestion core supplies the contract;
no historical application source body, private schema, query, forecasting policy,
business formula, record or operational configuration is exported.

Both calculation APIs require a clean ingestion batch and one contiguous
ordinal series. They refuse partial batches, conflicts, missing periods, mixed
series, invalid parameters and insufficient history. Evaluation exposes only
the earlier prefix to each prediction and does not silently adjust its start.
The core has no operational file, network, process or provider adapter. Real
inputs, predictions and scores remain private application data.

The dedicated workflow requires 38 evaluator tests and the 21 original
ingestion tests without skips on Windows/Ubuntu Python 3.12/3.13. It also runs
the actual fictional demo and collection documentation checks. Exact selected
files, snapshot equality and independent generated-case evidence are reviewed
before merge. These are bounded arithmetic checks, not production forecast
acceptance, anonymization or whole-repository confidentiality clearance.

See [usage](../tools/forecast-baseline-evaluator/README.md),
[methods and contracts](../tools/forecast-baseline-evaluator/FORMAT.md),
[rationale](../tools/forecast-baseline-evaluator/ARCHITECTURE.md) and
[validation limits](../tools/forecast-baseline-evaluator/VALIDATION.md).
Notification/outbox and other operational integrations remain separate private
drafts for later review. MIT applies only to the selected original source and
retained first-party reuse; caller inputs and runtimes retain their own terms.
