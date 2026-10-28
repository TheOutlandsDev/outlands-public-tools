# Design, methodology and numerical conventions

Build the whole experiment loop before adding sophisticated learners: declare data timing and independent groups, freeze an experiment, fit a reproducible baseline, choose decisions on validation, explicitly evaluate later data, retain review and export inspectable artifacts. Keep original operating bindings and all instance records outside public source.

## Leakage boundaries

Feature availability is checked row by row before fitting. A retrospective correction is usable only if its declared value was already available at the decision. This software cannot independently establish that history, detect a disguised target feature, identify duplicate content under different group IDs or infer the true unit of independence. Those remain data-design responsibilities.

Strict chronological gaps and label cutoffs keep unfinished earlier outcomes out of later-stage decisions. Group membership is checked across decision windows before purging; a delayed row cannot silently hide a crossing group. Dropping rows may alter representation: the counts and exclusion reasons are visible, not a guarantee of unbiased evaluation.

Only retained training rows fit means, scales, coefficients and prevalence. Validation selects a threshold from an explicit fixed grid. Test rows contribute no preprocessing, model updates or threshold choice. Invariance tests alter validation/test features and outcomes to check the relevant boundaries. Test evaluation is stored separately and idempotently; it is not an access-control system. Operators can still adapt future experiments to viewed results, requiring a fresh final holdout.

## Learner

For each feature, calculate its observed-training mean and population standard deviation. Missing values use the mean, giving standardized value zero. Variance is over observed values only, not mean-imputed rows. A scale below 1e-12 uses one and records a constant/tiny-scale flag. A feature with no observed training value is refused.

Initialize coefficients/intercept to zero. On each full-batch step, `p = sigmoid(intercept + sum(weight[j] * x[j]))`. Weight gradient is mean `(p-y)*x[j] + l2*weight[j]`; intercept gradient is mean `(p-y)`. Update with the fixed learning rate for the configured iterations. This corresponds to mean binary cross-entropy plus `l2/2 * sum(weight**2)`; the intercept is unpenalized. Stable sigmoid branches avoid exponential overflow. The budget is reproducible, not a convergence or optimality certificate. Floating-point results can differ slightly by platform.

The constant baseline uses training prevalence. It independently chooses its threshold on the same validation grid so a thresholding disadvantage is not hidden in the comparison. Model and baseline threshold ties prefer closest to .5, then lower. Precision/recall/F1 undefined cases are explicit nulls.

## Metrics

AUC is the positive-rank sum formula using average ranks for ties, equivalent to positive/negative pairwise wins with half credit for tied scores. AUC is null without both outcome classes. Average precision accumulates change in recall times precision at each distinct descending score, grouping ties; it is null without positives. This is non-interpolated AP, not trapezoidal precision-recall area. See the [primary AP definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html); no library implementation was copied.

Brier is mean squared score error. Log loss uses scores clipped to [1e-15,1-1e-15] to retain finite values at endpoints. Confusion uses `score >= threshold`. Five equal-width reliability bins include score 1 in the last bin; empty means/fractions are null. Scores are marked uncalibrated. Brier and log loss mix discrimination and calibration effects; a lower Brier alone does not establish calibration. See the [primary calibration discussion](https://scikit-learn.org/stable/modules/calibration.html).

Independent tests use pairwise AUC, hand-derived grouped AP, literal confusion/Brier/log-loss examples, a one-step gradient oracle and train-only preprocessing arithmetic. Golden synthetic metrics test this implementation, not an original system or real-world task.

## Persistence and UI

Immutable dataset/configuration/result hashes bind experiments and their evaluation parents. Append-only SQL triggers, exact schema/version checks and optimistic review versions support consistency; hashes and triggers are not tamper-proof storage. One application lock serializes preparation, evaluation and export. Native file guards and stopped-session recovery adapt existing public code without weakening POSIX protections.

The UI separates configuration drafts from saved result selection. Forms synchronize explicit configuration JSON; advanced JSON is applied explicitly. Failed requests retain drafts. Current-artifact review is distinct from planning a later experiment. SVG charts and tables derive from saved results; no external graph library, analytics, fonts or service calls are used. Caller values are literal DOM text, while static report JSON is HTML-escaped. The session token is local request protection, not identity authentication.

Exports are new directories with a manifest last. Failed writes may retain partial directories for manual review; no deletion or automatic cleanup is performed. Database backup is schema-verified but not a full-instance restore exercise. Limits intentionally suit small local educational datasets, not high-volume training or production deployment.
