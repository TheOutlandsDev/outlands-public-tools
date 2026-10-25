# Supported format and report contract

## Source and XML parser

Schema 1 accepts UTF-8 bytes containing XML 1.0 with root `svg` in the exact
`http://www.w3.org/2000/svg` namespace. Prefix choice is irrelevant. An absent
namespace or a different URI is not inferred as SVG. A UTF-8 BOM is supported.
An XML declaration may omit encoding or declare UTF-8/UTF8. Other declarations,
malformed XML and duplicate attributes fail. Internal and external DTD/entity
declarations are rejected by parser callbacks before declared entities are used.
Built-in XML entities and numeric character references remain supported.

The public `inspect(bytes, include_details=False)` API requires Expat >=2.7.2,
keeps parser reparse deferral enabled, disables parameter entity parsing and
does not install a resolver that accesses files or a network. Processing
instructions are not followed; their presence makes coverage incomplete.
Input/structure limits are explicit, but this is not a universal hostile-input
or filesystem sandbox. Keep Python/Expat current and use stable local copies.

## Declared dimensions

`width` and `height` accept bounded finite decimal/scientific literals, optionally
followed immediately by `%`, `px`, `em`, `ex`, `cm`, `mm`, `in`, `pt`, `pc`, `q`,
`rem`, `ch`, `vw`, `vh`, `vmin` or `vmax`. ASCII unit case is normalized to lower
case; no conversion occurs. Unitless numbers are labeled `user_units`. Negative
values, unknown units, functions and values such as `auto` are outside the
supported literal subset. Zero values are retained with a review finding.

`viewBox` accepts four whitespace/comma-separated finite decimal numbers; its
width/height must be positive. Origins may be negative. Numbers have at most
64 characters, decimal exponents with absolute value <=64, and absolute value
<=1e12. JSON uses exact decimal strings, not binary floating-point conversions.
Invalid/unsupported tokens are not echoed. Missing declarations remain absent,
not inferred from child geometry, CSS or browser defaults.

## Markup observations

Known selected SVG element names are classified locally. Script, foreignObject,
animation/set/mpath, `a`, `image` and `feImage` markers produce review findings.
Attributes whose local name begins with `on` (case-insensitive observation) are
flagged. This can conservatively include unknown attributes; it does not evaluate
whether a specific browser treats them as an event handler. `xml:base` is recorded
without using its value. Unknown SVG names, foreign elements/attributes/namespace
declarations and animation timing fields make coverage explicit. No document
text, metadata, namespace URI, script body or event-handler value is copied to
the default report.

## References and IDs

- Unqualified `href` and XLink `href` are observed as separate declarations.
  If both occur, no precedence is selected.
- Supported presentation reference attributes are `fill`, `stroke`, `filter`,
  `clip-path`, `mask`, `marker`, `marker-start`, `marker-mid`, `marker-end`,
  `cursor` and `color-profile`. Their literal CSS URL tokens are observed.
- Literal `url(...)` accepts an unescaped quoted argument or an unquoted argument
  without internal whitespace, quotes, parentheses, comments or backslashes.
  The tokenizer skips ordinary strings and complete comments outside URL tokens.
- Literal `@import "..."`/`'...'` is observed. A literal `@import url(...)` is
  counted as a URL token. Media queries/at-rule semantics are not evaluated.
- Stylesheets and inline styles always require review. Any CSS escape, non-ASCII
  CSS, unsupported string/URL, unknown function or at-rule has explicit coverage.
  Escaped identifiers such as `u\72l` are **not guessed or decoded**. This can
  miss their reference payload, but cannot produce complete coverage: the escape
  itself requires review. The tool is not a full CSS grammar/cascade evaluator.

Reference kinds are `internal_fragment`, `unsupported_fragment`, `empty`,
`uncertain_text`, `data`, `active_scheme`, `external_network`, `external_file`,
`external_relative` and `unknown_scheme`. These are bounded lexical categories,
not URL validity, reachability or rendering behavior. XML character references
are already decoded by the XML parser. Data payloads are not decoded. Relative
references and base URLs are not resolved. Processing-instruction and foreign
markup references are outside the supported discovery subset.

Only a fragment matching `[A-Za-z_][A-Za-z0-9_.:-]{0,127}` is compared, exactly and
case-sensitively, with declared unqualified `id` attributes. Percent-encoded,
Unicode and SVG-view/XPointer-style fragments stay uninspected. ID declarations
outside this fragment subset receive coverage. Resolution states are
`resolved_unique`, `missing`, `ambiguous_duplicate_id` and `not_inspected`.
One ID-text match does not establish a valid target element, absence of cycles,
CSS binding or browser acceptance. Duplicate IDs are reported; no winner is chosen.

Opaque node numbers follow XML start-element order. Opaque reference numbers
follow observation order. ID report numbers follow sorted source ID strings.
Default reports omit actual ID/reference strings; these numbers are structural
labels, not anonymization or stable cross-document identities.

## Reports and limits

The CLI writes `report.json`, `report.html` and `MANIFEST.json` in a fresh directory.
The manifest records lengths and SHA-256 of the two reports. It is a consistency
record, not a signature or proof of source ownership. HTML contains only escaped
report text and local inline CSS; it embeds no source SVG, script, active link,
image, font or external resource. Raw URL/ID strings appear only when private
`--include-details` was selected; HTML still escapes every displayed value.

Limits are fixed in this release and included in the report:

| Work | Bound |
| --- | ---: |
| Input bytes | 2 MiB |
| Elements / nesting | 20,000 / 64 |
| Total / per-element attributes | 100,000 / 64 |
| Attribute value characters | 16,384 |
| Character data | 1,048,576 |
| One CSS input / total CSS characters | 65,536 / 262,144 |
| References / findings | 2,000 / 2,000 |
| Each encoded report | 8 MiB |
| Namespace declarations | 1,024 |
| Namespace URI / prefix characters | 2,048 / 256 |
| ID characters | 1,024 |

Exceeding a bound fails the whole inspection. No partial output is called a pass.
Path/handle identity observations detect supported source changes; hostile races
and native filesystem-operation timing remain outside the guarantee. A failed
report write may leave its new partial directory; it never replaces old outputs.

Exit 0 means `NO_SCOPE_FINDINGS` in this subset; exit 1 means `REVIEW_REQUIRED`;
exit 2 means `INCOMPLETE`. Neither a successful status nor a manifest certifies
safe rendering, sanitization, complete syntax validity, artwork rights or quality.
