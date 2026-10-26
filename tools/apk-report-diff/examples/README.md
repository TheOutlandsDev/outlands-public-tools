# Fictional saved metadata

`generate.py --output ABSOLUTE_NEW_DIRECTORY` creates five UTF-8 badging-like
text files using fictional package/library names and hand-authored metadata.
The parent must exist; existing output destinations are refused.

| Pair | Expected result |
| --- | --- |
| `before.txt` / `same.txt` | Exit 0, no supported change or coverage issue. |
| `before.txt` / `after.txt` | Exit 1, six supported field/declaration changes. |
| `before.txt` / `unsupported.txt` | Exit 1, unknown-row coverage; missing library removal held. |
| `before.txt` / `duplicate.txt` | Exit 1, duplicate beta library held; other supported changes remain visible. |

Use `--include-details` with the inspector to read fictional values in the
report. Default omission is not anonymization for real reports. Do not commit
generated private reports. These samples are not genuine APK captures or
evidence of Android runtime compatibility. See the [main guide](../README.md).
