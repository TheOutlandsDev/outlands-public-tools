# Contributing

Bug reports, usability improvements and format proposals are welcome through
the [public issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose Offline Session Telemetry Analyzer and include the source commit, OS,
Python version, exact steps, expected behavior and a minimal fictional fixture.
Do not attach real logs, game files, player identifiers, credentials or private
reports. Hashes and aggregate statistics can still identify a real capture.

Discuss new producer dialects as explicit grammar changes. Preserve missing and
invalid sample distinctions, exact numeric types, independent denominators,
unknown coverage and end-marker ambiguity. Avoid treating a captured count as
an entity identity or a passing report as runtime proof. Tests should exercise
meaningful malformed/partial input and the actual CLI using generated data.

Run both documented checks. After reviewing a source change, deliberately update
the explicit source inventory with `python -B source_check.py --write-manifest`
and rerun the source gate and tests. An unsigned source inventory records bytes;
it does not prove a contributor's rights or that every possible secret is absent.
Contributions must be material you may license under MIT; retain required notices
and keep inspected third-party data outside the repository.
