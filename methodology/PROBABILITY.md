# Probability terms and evidence

Use these definitions with the [general terms](TERMS.md). The tool guides define
exact schemas. All examples use invented HVAC or game records.

| Term | Plain meaning | Precise meaning in these tools |
| --- | --- | --- |
| Probability vector | One stated chance for each possible class. | One decimal string in [0,1] per declared label, totaling exactly one. Valid arithmetic does not establish that the chances describe reality. |
| Positive label | The event whose probability is being scored. | An explicit label ID in the binary contract. Its supplied outcome is encoded as 1; the declared negative label is 0. Label order is never inferred. |
| Cohort | The cases selected for one calculation. | Explicit case IDs and revisions, with prediction/outcome references pinned to those exact cases. Incomplete evidence withholds the full aggregate. |
| Squared probability error | Distance between a stated probability and a supplied outcome. | For probability p and outcome y, compute (p-y)^2. Report the total and full-cohort mean as exact fractions. This binary mean is commonly called the Brier score under the stated encoding. |
| Reliability bin | A caller-chosen probability range. | [lower,upper), except the final bin includes probability one. Compare the mean stated probability with the supplied positive-outcome fraction. Empty-bin rates are null. |
| Weighted absolute bin gap | A summary of differences within the chosen ranges. | Sum (bin count / cohort count) times absolute bin gap. It depends on the bin choices and is descriptive, without a significance or calibration claim. |
| Calibration | Agreement between stated probabilities and event frequencies. | A statistical property requiring separately justified data and evaluation. Passing these structural checks or viewing a small reliability table does not establish it. |
| Calibration map | A proposed rule for changing a probability. | A declared piecewise-linear map with endpoints at input zero and one and nondecreasing outputs. The checker compares shape and revisions; it neither fits nor applies the rule. |
| Exact decimal | A number supplied without binary floating-point rounding. | A decimal string with at most six fractional digits in [0,1]. Arithmetic uses rational fractions. Three values of 0.333333 total 999999/1000000 and fail the exact-one rule. |

`PASS` means the supplied declarations met the tool's rules. `REVIEW_REQUIRED`
can mean missing evidence, an invalid vector or partition, or a valid map change
that needs review. Exit codes are 0, 1 and 2 for pass, review and fixed refusal.
A pin links declared data under a specified encoding; it does not authenticate
outcomes. Real predictions, labels, fitted maps and reports belong in private storage.
