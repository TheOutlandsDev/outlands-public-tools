# Offline Backend Verification Report Runner

Run trusted checks and return a report with pass, warning, and failure counts
and a reproducible SHA-256 fingerprint. The package preserves the original
report logic and all five tests, with fictional checks and a fixed example
clock. The example uses in-memory observations.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/backend-verification-runner-v0.1.0)
- [Run the fictional example](SETUP.md)

Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2
and pinned Pydantic 2.14.3. Supply only trusted read-only callbacks and public
details and metrics. The runner executes callbacks directly.
