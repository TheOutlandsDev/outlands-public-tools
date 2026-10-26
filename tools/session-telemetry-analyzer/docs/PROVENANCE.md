# Provenance and MIT scope

The owner's personal `Summarize-QuakeBrainTelemetry.ps1` helper summarized saved
event logs using population, tracking and visibility counters. This publication
uses that generic saved-evidence use case in a fresh reusable implementation.
It does not copy game/plugin code, fixed installation paths, private telemetry,
player identities or deployment settings.

The original helper remains intact and fingerprinted in the private batch
review. The owner identified the helper as personal work; this selected-source
review is not independent proof of exclusive historical authorship. The new
parser, tests, guides and fictional generator are original AI-assisted MIT work.
First-party file/report safeguards and their tests are reused from this
collection under MIT so the module can be downloaded independently.

The public implementation intentionally changes the earlier summary behavior:
missing and invalid fields do not become zero samples, each metric has its own
valid denominator, exact decimal declarations avoid binary-float conversion,
unknown/malformed input remains explicit and multiple end rows do not supply a
cumulative dropped-line winner. No behavior of a live producer is certified.

Primary format/runtime references checked on 2026-10-26:

- [JSON Lines format](https://jsonlines.org/). The tool reports its explicit
  BOM/blank-line compatibility extensions rather than claiming conformance.
- [Python JSON library](https://docs.python.org/3/library/json.html).
- [Python decimal library](https://docs.python.org/3/library/decimal.html).

These references retain their own rights. No upstream parser implementation,
runtime, game implementation, third-party fixture or SDK binary is bundled or
granted a new license here. Python is separately installed under its applicable
terms. MIT covers this original source, authored documentation/tests, first-party
reuse and generated fictional examples. Inspected inputs retain their own rights.
Inspection and report creation do not grant permission to publish raw captures.

Validation uses generated saved records only. No game, plugin, live telemetry
collector, runtime state, multiplayer session or producer integration was tested.
