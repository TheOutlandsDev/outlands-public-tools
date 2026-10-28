# Worked methodology examples

These completed design records use invented Orchard inputs. Their expected
results are specifications; run the commands to record observations on your own
machine. The release packaging workflow runs the same examples on Windows and
Ubuntu and retains its result with the package checks.

1. [Release review and exact source inventory](release-review.md): preserve a
   baseline, edit a fictional file, detect the change and verify a ZIP inventory.
2. [Dependency change review](change-review.md): distinguish changed declarations
   from equivalent formatting without claiming compatibility or installing them.
3. [Documentation handoff](document-handoff.md): reproduce a missing-link failure,
   correct it, then record the actual result and remaining acceptance work.

Use Python 3.12/3.13. The complete or release-QA package supplies the four tools.
Run from the extracted package root. Replace the placeholder with a NEW absolute
directory beneath an existing private scratch parent outside the extracted tree:

```text
python -B methodology/worked-examples/run_examples.py --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

No dependencies are installed and no network request, native device operation,
application deployment or destructive file move is performed. The script writes
only its newly created fictional workspace and retains all files on failure.
It refuses an existing destination. Keep real inventories and results private.

Expected stdout and `observed-results.json`: `examples_passed: 3`,
`command_checks: 8`; unchanged inventory matches, edited inventory requires review,
equivalent locks match, changed locks report differences, and the missing document
fails before its correction passes. JSON formatting and tool-specific report
fields may include more detail than this summary.

Other package families retain their own fictional examples beside each tool.
The runnable three-example sequence is provided by complete/release-QA only.
For all eight blank templates, use [the methodology index](../README.md).

## Turning an example into an engineering record

Copy the intake, decision, validation and handoff templates into your private
project. Record the actual source revision and platform; preserve failed and
skipped checks. Replace expected outcomes with observations only after execution.
Publish a separate reviewed fictional export rather than operational records.
