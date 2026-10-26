# Contributing

Usability ideas, supported-format proposals, bug reports and recovery test cases
are welcome through the collection's
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose the Mod Profile Activation Manager bug or suggestion form. Include the
source commit, OS/Python/Tk version, exact steps, expected behavior and a minimal
fictional fixture created by the example generator or a small script.

Do not attach real game/mod assets, save files, proprietary configurations,
workspace journals, manifests, identifying screenshots, credentials, private
paths or material you lack permission to publish. Runtime data belongs in a
private directory outside the source checkout. Removing names is not proof that
a report or data set is anonymous or cleared for redistribution.

Keep preview separate from mutation and verify managed ownership before every
change. Preserve sources and retained copies. New behavior needs meaningful
tests for data integrity, unexpected files, refusal paths and interruption
boundaries. A test skip is not a pass. Never remove a hash/path/lock safeguard
to make a failing fixture pass. Avoid dependencies unless their value and
license/runtime costs are clear.

Run the module's source gate, engine/CLI tests and native Tk tests described in
[validation](docs/VALIDATION.md). Review source changes before deliberately
refreshing the explicit SOURCE-MANIFEST.json. Use generated inputs only; do not
exercise a contribution against a live game or valuable directory for acceptance.

Contributions to the original program, tests, guides and synthetic fixtures are
offered under this module's MIT license. Preserve required notices. Input content
and third-party implementations retain their own applicable rights.
