# Fictional telemetry examples

Run `python -B examples/generate.py --output NEW_ABSOLUTE_DIRECTORY` from the
module folder. The parent must exist and the destination must be new. The
generator creates three original small text files only, outside the source
checkout; it never reads an installation or copies actual telemetry.

| File | Expected analyzer exit | Observations |
| --- | --- | --- |
| `clean.jsonl` | 0 | Six events, three snapshots; valid player mean `6/2`, bot mean `12/2`, tracked-active mean `4/2`; visibility `1/2`; one zero-drop end declaration. |
| `review.jsonl` | 1 | Boolean population and invalid tracking container, malformed last record and two end markers. Dropped-line value remains null/ambiguous. |
| `missing-fields.jsonl` | 0 | Two snapshots, one explicit player zero. Missing fields are not zero-valued observations; unobserved means are null. |

Fractions are unreduced numerator/denominator objects in JSON, not displayed
floating-point estimates. Read the main [quick start](../README.md) for quoted
Windows/Linux commands and use a different fresh output folder for each run.
All examples are invented metadata and are not game/plugin acceptance evidence.
