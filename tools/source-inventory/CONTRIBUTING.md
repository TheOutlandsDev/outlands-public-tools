# Contributing

Suggestions and reproducible bug reports are welcome in the shared
[OUTLANDS Public Tools issues](https://github.com/TheOutlandsDev/outlands-public-tools/issues).
Use the Source Inventory forms and include the source commit, OS/Python version,
exact supported options and a minimal generated input example.

Do not attach real project inventories, private paths, credentials, datasets or
third-party source you lack rights to share. File names and hashes can disclose
private material even when file contents are absent.

Run `python -B -m unittest discover -s tests -v` from this module. Keep default
CSV/JSON compatibility and existing exclusion, byte/count/entry, link, change-
detection and exclusive-write safeguards. New behavior needs meaningful cases
for success, failure and applicable platform semantics. Do not weaken a check
merely to make a fixture pass. Explain any platform skip and distinguish native
filesystem evidence from mocks.

Original contributions are offered under this module's MIT license. Retain all
required third-party attribution and license notices. A contribution does not
establish ownership of unrelated historical inputs.

For classification changes, use the dedicated
[bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=inventory_rules_bug.yml)
or [suggestion](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=inventory_rules_suggestion.yml)
form. Keep generated input hashes/counts internally consistent and include an
expected first-match category, complete matching-rule IDs and unmatched/overlap
counts. Arbitrary regex execution and implicit source rescanning are outside
the current [classification contract](docs/CLASSIFICATION.md). Do not present
user categories as verified license or safety classifications.
