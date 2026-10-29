# OUTLANDS | Message Template Renderer

Render literal text and escaped HTML with exact declared string variables. Independent source CLI/library; Python 3.12/3.13,
standard library only, [MIT licensed](LICENSE).

## Fictional example

From the collection root (replace the EML example placeholder with a fully
spelled existing private directory outside the source tree):

```text
python -B tools/message-template-renderer/render.py --template tools/message-template-renderer/examples/template.json --values tools/message-template-renderer/examples/values.json
```

No inputs are discovered automatically. These examples contain only invented
records and reserved example.invalid addresses. No real mail, private application
source, templates, routing, endpoints, credentials or delivery records are bundled.
No provider adapter, network call, send, retry, process launch or target update.
Combined packages and browser applications are deferred.


## Contract and limits

`render(template_raw, variables_raw)` accepts UTF-8 JSON bytes. Exact template
fields: `format: outlands-message-template-v1`, `template`, `variables` (unique
declared identifier list). Values fields: `format: outlands-message-values-v1`,
`values` (exact string-valued object). Only `{{name}}` substitutions are supported;
unmatched braces, expressions, attributes, includes and undeclared/unused variables
are refused. Replacement values are inserted once, never reparsed as templates.

Template: nonblank, at most 4,096 characters; 32 variables; 128 placeholder uses;
each value at most 2,048 characters; rendered text at most 65,536 UTF-8 bytes.
Controls, Unicode format characters/bidi controls and line/paragraph separators
are refused; LF/TAB are allowed. Empty string values are allowed. No coercion.

Output always contains supplied text values. HTML is one fixed `<pre>` wrapper
with **all literal template and inserted content HTML-escaped**. Caller-authored
HTML, scripts, attribute interpolation and URL templating are unsupported. No
browser is started; no visual rendering or client compatibility is claimed.
This is body preparation, not a subject/header renderer or MIME composer.


## Files, diagnostics and privacy

See [checked Windows/POSIX I/O](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). JSON parsing rejects duplicate keys, floats,
nonfinite numbers, invalid Unicode, excess depth/nodes and unknown fields.
Declared strings are generally at most 4,096 characters. Reports serialize as
ASCII JSON. `--out` creates a new external file only; parent must exist. No
overwrite, source-tree output or automatic cleanup/retry after write failure.
Failed writes may leave retained unconfirmed output; choose a new path.
Windows ACLs inherit from the chosen directory. Inputs must be trusted/quiescent.

Exit codes: 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption.
`--help` shows static usage; errors omit supplied values/paths. Default stdout
can contain private values or fingerprints. Output hashing and JSON escaping
provide no anonymization. Structural acceptance is not permission to publish
real inputs or reports, nor a secret/content scanner. No real delivery or
mail-client rendering is qualified.

From this tool directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
