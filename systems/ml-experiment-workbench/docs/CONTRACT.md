# Dataset, experiment and artifact contracts

## Dataset

Exact fields: `format`, `dataset_id`, `title`, `feature_names`, `rows`. Format is `outlands-ml-dataset-v1`. IDs/feature names are portable ASCII tokens beginning with a letter, then letters/digits/dot/underscore/hyphen, maximum 64 characters; reserved Windows device names and trailing dots are refused. Feature names are case-insensitively unique, one to eight. Title is bounded plain text. Rows are sorted by decision day and row ID before canonical hashing; feature order is retained.

Every row has exactly `row_id`, `group_id`, `decision_day`, `label_available_day`, `features`, `feature_available_day`, `outcome`. Row IDs are case-insensitively unique. Repeated exact group IDs are allowed, but case-only aliases are refused. Days are integers 0–1000000; outcome is integer 0/1, never Boolean. Feature mappings must contain exactly the declared names. Numeric features are finite in [-1000000,1000000]; null requires null availability, while observed features require integer availability no later than decision. Label availability must be at or after decision.

Canonical JSON uses ASCII escapes, sorted keys and compact separators. Immutable dataset hash binds every retained row, label, timing value, title and feature order. Existing ID with changed content is refused; identical canonical content is idempotent. Hashes establish consistency, not truth or signed provenance.

## Experiment

Exact fields: `format`, `experiment_id`, `dataset_id`, `dataset_sha256`, `split`, `learner`, `thresholds`. Format is `outlands-ml-experiment-v1`; dataset hash must match an imported immutable dataset. Existing experiment ID with changed configuration is refused.

Split has exactly `train_end_day`, `validation_start_day`, `validation_end_day`, `test_start_day`, `test_end_day`, `as_of_day`, positive bounded integers. Require train end < validation start < validation end < test start < test end <= as-of. Train begins at ordinal day zero. Decision windows are half-open; intentional gaps are excluded. Group IDs cannot appear in more than one decision partition, checked before delayed-label exclusion.

Train rows with label availability >= validation start are purged. Validation rows with availability >= test start are purged. Test rows with availability > as-of are pending and excluded. All other outside-window rows are excluded with an explicit reason. Retained train and validation each require at least two rows and both outcome classes; retained test requires at least one row and may contain a single class.

Learner fields: `iterations` integer 1–600; `learning_rate` numeric .001–1; `l2` numeric 0–1. Thresholds are one to 19 unique finite numbers in [.01,.99], sorted canonically. Numeric Boolean stand-ins are refused.

## Preparation and evaluation

Preparation stores configuration/hash, dataset hash, numeric model/hash, training metrics, validation metrics/predictions, validation threshold grids, selected model/baseline thresholds and partition membership/cohort hashes/exclusions. Test metrics/predictions are absent. Partition metadata may reveal row IDs and availability; this is not holdout secrecy.

Evaluation request is exactly `experiment_id`, `expected_sha256`, matching the prepared hash. It uses the frozen model, train-only preprocessing and selected thresholds. Evaluation is a separate append-only record, one per experiment; repeating the same request returns the existing record without recomputation. It binds the prepared/model hashes and exact test cohort, metrics and predictions. It does not prevent the operator viewing labels or trying new experiments after seeing results. A new evaluation requires a new experiment; statistical independence requires a separately governed fresh holdout.

## Review, comparison and export

Review request is exactly `experiment_id`, `artifact_sha256`, `expected_version`, `status`, `actor`, `note`, `checks`. Artifact is the evaluation hash when present, otherwise preparation hash. Status is pending/approved/rejected. Four strict Boolean checks quality/privacy/rights/context must all be true for approval. Actor is bounded text; note may be empty. These are private local assertions. Row version starts at zero before review. Stale artifact/review versions refuse writes; evaluation creates a new current artifact with pending review.

Comparison reports validation values with explicit labels. Test deltas exist only when both evaluations exist and hashes of the complete test rows match. Different configurations can change cohorts, making direct deltas unavailable. Matching cohorts alone do not establish fair model selection or independent evaluation.

Export requires current-artifact approval and a recorded evaluation. Seven payload files contain configuration, numeric model, preparation, evaluation, review, summary and escaped static HTML; `manifest.json` is written last. Format `outlands-ml-report-v1` binds artifact, review version, dataset/model hashes, implementation version, per-file bytes/SHA-256 and `public_release_authorized: false`. Selection holds the application lock. Partial directories remain on failure; existing outputs are never replaced. The raw source dataset is not copied, but preparation/evaluation still contain identifying rows and outcomes. Treat the full report as private.

JSON model format `outlands-logistic-baseline-v1` is inspectable numeric data, not executable serialization. No arbitrary model importer or pickle loader exists. Database backups include all stored private datasets, models, results and reviews, but exclude inbox/report directories. None of these contracts clears future inputs for disclosure.
