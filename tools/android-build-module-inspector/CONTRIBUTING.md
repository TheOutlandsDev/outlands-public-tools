# Contributing

Suggestions, usability improvements and supported-format proposals are welcome
through the collection's [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's bug or suggestion form and include the source commit, OS,
Python version, expected behavior and a minimal fictional reproduction.

Do not attach real firmware/source trees, proprietary build files, credentials,
private inventories, vendor implementations or unredacted reports. A hash or
default field omission does not anonymize source material. Use only examples
you have rights to publish.

Keep grammar support explicit. New syntax needs tests for both accepted cases
and misleading lookalikes; unsupported input must retain uncertainty rather
than produce invented missing-module or collision conclusions. Do not follow
includes, evaluate Make expressions, run a build or search a live source tree.
Keep the shared first-party helpers compatible with standalone module usage.

Run the documented source check and unittest suite. After deliberately reviewing
source changes, refresh the exact unsigned inventory with
`python -B source_check.py --write-manifest` and rerun the checks. Generated
fixtures/reports belong in an external private workspace. Contributions to
the original code/docs/tests are offered under this module's MIT license.
