# XML Workflow Checker

Validate and compare an invented workflow-graph schema, offline. Python 3.12/3.13,
standard-library runtime, MIT TheOutlandsDev. This is fresh generic code; no
original recipe, manufacturing schema, route, formula or operating record is
included. It is independent of the collection's metrology XML Recipe Inspector.

Run from this tool directory:

```text
python -B workflow.py --input examples/before.xml
python -B workflow.py --input examples/after.xml --before examples/before.xml
```

The first returns exit 0/PASS. The second returns exit 1/DIFFERENCES: the invented
second revision adds an explicit rework transition. `--before` is optional;
there is no automatic file discovery or reference loading. Library:
`workflow.check(xml_bytes, before_bytes=None)`. Keep the trusted tool directory
on the import path; no sibling tool installation is required.

## Invented schema

The exact examples are [before](examples/before.xml) and [after](examples/after.xml).
An unnamespaced `workflow` has `id` and integer-text `version` attributes, then
exactly `steps` and `transitions`. Steps have unique `id` and a `kind` of `start`,
`process` or `end`. Exactly one start and at least one end are required.
Transitions have unique `id`, `from`, `to` and `kind` (`forward` or `rework`).
IDs are 1–48 lowercase ASCII identifier characters starting with a letter.
Versions are canonical integer text 1–1,000,000. Unknown fields/elements, mixed
text, duplicate edges, duplicate IDs and missing references are refused.

Forward transitions must form an acyclic graph. Every step must be reachable
from the start and have a forward path to an end. The start cannot have a forward
input, and an end cannot have a forward output. A rework transition must point
to a distinct forward ancestor of its source. Intentional rework cycles in the
combined graph are allowed; unmarked forward cycles and self-transitions require
review. The tool assigns no costs, yields, resources, durations or schedules and
does not execute the graph.

Comparison matches steps/transitions by ID, independent of element order and XML
whitespace. Changed/added/removed steps and transitions are reported in sorted
order. Raw byte hashes remain distinct for different formatting. Workflow IDs
must match, versions cannot regress, and changed graphs require an increased
version. A version-only increase is a difference. If either graph needs review,
`changes` is null and there is no qualified comparison. Version numbers and IDs
are caller declarations rather than proof of revision authenticity.

## Bounds, privacy and output

At most 4 MiB input, 128 steps, 512 transitions, XML depth 32, 50,000 XML elements
and 2 MiB text/attribute characters. DTDs, entity declarations, processing
instructions and comments are refused, including UTF-16 declarations. XML
character references are supported. No namespace adaptation, XInclude expansion,
remote fetching, image opening or command execution occurs. This schema is not a
parser for BPMN, vendor recipes or arbitrary production workflows.

Private ASCII-escaped JSON on stdout includes graph identifiers, relationships,
versions, issues and exact byte hashes. It is not an anonymized report.
`--out NEW_PRIVATE_REPORT.json` creates only a fresh external file; no existing
report is replaced. See [I/O limits](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). Exit 0 PASS/MATCH; 1 DIFFERENCES/review required;
2 structural/argument/I/O refusal; 130 interruption. A valid graph is not proof
of operational safety, correct business policy or authorization to run it.
