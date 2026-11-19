# Offline Typed Observation Result Comparator

Compare two saved JSON result sets by exact typed values and duplicate counts.
Each row has three text fields and two timestamps. The summary gives matched
and unmatched counts, regardless of row order.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/typed-observation-result-comparator-v0.1.0)
- [Usage guide and fictional inputs](SETUP.md)

This standalone tool retains the original typed row validation, comparison rules,
and four offline tests. It uses the Python standard library. Qualification
covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
