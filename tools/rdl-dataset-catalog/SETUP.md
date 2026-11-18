# Build and check a fictional RDL catalog

Compare the downloaded ZIP with `SHA256SUMS.txt`. On Windows, use
`Get-FileHash -Algorithm SHA256 .\rdl-dataset-catalog-0.1.0.zip`. On Ubuntu, use
`sha256sum rdl-dataset-catalog-0.1.0.zip`. Extract the ZIP and open a terminal in
the extracted folder with Python 3.12 or 3.15. The tool uses the standard
library. Substitute your installed Python executable for `python` if needed.

```text
python -B -m rdl_query_lab.build_catalog --source examples --out demo-catalog
python -B -m rdl_query_lab.build_catalog --source examples --out demo-catalog --check
```

The example writes `catalog.json`, `datasets.csv`, `review_queue.csv`,
`summary.md` and two command files for two fictional reports and three datasets.
The select command includes a Unicode character, an XML entity and multiple
lines. Its extracted file contains the UTF-8 bytes of the parsed `CommandText`,
including leading spaces and trailing newline. XML parsing decodes entities and
normalizes XML line endings before the builder hashes and writes the command.

`--check` compares filenames and bytes without writing. Change the text of one
generated command file, then run `--check` again. It reports a content mismatch
and exits 1. It also reports missing and extra files. Use a fresh output folder
for each build. The builder can rewrite expected outputs in an existing folder
and refuses a build when unexpected files are present.

Use trusted `.rdl` inputs and keep the destination separate from them. The
catalog and commands can reproduce sensitive source text. Keep generated files
private when working with operational reports. The dependency tiers are clues
for review. SQL, expressions, stored procedures and report code are never run
by the builder.

Run all ten retained unit cases with `python -B -m unittest discover -s tests -v`.
`VALIDATION.json` records the four native profiles, parser versions, independent
ZIP rebuilds and eight checks from the extracted copy. Source adaptations are
limited to the default input path and neutral labels in the builder, classifier,
fixtures and expected test values. Test logic is unchanged.
