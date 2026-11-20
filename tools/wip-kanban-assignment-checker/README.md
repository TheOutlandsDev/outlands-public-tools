# Offline WIP-to-Kanban Assignment Checker

Route prepared work-in-progress rows into K1 through K6 using a supplied configuration. Run a preflight to see invalid rows, or produce a complete assignment with bucket counts, material totals, yield percentages, and SHA-256 digests.

[Setup and fictional walkthrough](SETUP.md) · [Download and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/wip-kanban-assignment-checker-v0.1.0)

The standalone package preserves the original routing, preflight, sorting, yield and digest logic. It replaces deployment-specific provenance fields and pinned source identifiers with an explicit local routing file. Check the routing file against your own approved baseline before using the output for decisions. Duplicate source rows are counted as separate rejected records.

The qualification workflow builds a deterministic source ZIP and tests a fresh extraction on Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2, Pydantic 2.14.3 and hash-pinned dependencies. Six adapted original functions run as nine test cases. Two additional tests cover conservation and duplicate-row accounting.
