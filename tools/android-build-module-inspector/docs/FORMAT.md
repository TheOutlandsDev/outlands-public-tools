# Supported declarations and report contract

Schema version 1 inspects a narrow, literal subset of selected BP/Make text.
An observed declaration is a source-text observation. It is not evaluated build
state, namespace identity, module availability or functional compatibility.

## Names and wanted files

Names are 1–256 ASCII letters/digits, underscores, dots, plus signs, `@` or
hyphens. They are case-sensitive literal strings. The tool does not strip `.so`,
derive names from paths, case-fold, normalize, evaluate escapes in Make or infer
global `//namespace:name` references. This subset does not validate all names
accepted by Android build tools.

A wanted file is UTF-8 text with one exact supported name per nonblank line.
Surrounding ASCII spaces/tabs and full-line `#` comments are ignored. Duplicate
requests are reported as coverage and retained once. Inline comments, expressions,
quoted names and unsupported characters are refused with exit 2. An explicitly
selected wanted file must contain at least one unique name.

## BP tokenizer and direct properties

The original tokenizer recognizes ASCII identifiers, JSON-style double-quoted
strings, punctuation, whitespace, `//` line comments and `/* ... */` comments.
Comment markers/braces inside strings do not become syntax. Strings may use
valid JSON escapes but cannot contain a literal newline. The parser never loads
a resource or executes text. Unterminated comments/strings or unsupported string
escapes produce coverage; ordinary malformed nested structures do likewise.
Resource/encoding/control limits instead produce exit 2.

Top level must be a sequence of `identifier { properties }` blocks. Each direct
property is `identifier : value`, separated by commas; a trailing comma is
accepted. A value is a nonempty token sequence with balanced nested `{}`/`[]`.
Other value syntax/types and nested properties are discarded without full
validation. This is intentionally not a full BP grammar validator. A literal
module name is exactly one string token in one direct `name` property, and must
satisfy the name subset above. Numbers, expressions, list values, missing names
and invalid literal names are unresolved. Nested `name` properties are not
module declarations. Strings that contain structural characters are never
accepted as opening/closing punctuation.

Duplicate direct property keys hold the entire declaration, even if a duplicate
is not `name`. If all recognized literal name candidates agree, the known name
can be retained as held; different/unknown candidates remain unresolved. A held
known name is not a confirmed unambiguous module.

`soong_namespace` and `package` blocks are consumed but not counted as named
modules; they add unevaluated-scope coverage. `soong_config_*` block kinds retain
their literal names only as held and add coverage. Other module types are not
looked up in a type registry. Top-level variables/assignments or any unsupported
top-level sequence stop inspection of the remaining file. Prior complete
declarations remain observations, and unmatched requests are held. Structural
failure in a current block does not emit a partially parsed declaration.

No namespace imports, package inheritance, defaults, aliases, visibility,
glob/file expansion, conditional property selection, generated module behavior
or effective build inclusion is evaluated. Equal names across selected files
may be valid in distinct namespaces or variants. Repetition is always labeled
an observation rather than a proven collision/build error.

## Make subset

Supported modules have the following literal structure:

```make
include $(CLEAR_VARS)
LOCAL_MODULE := example.alpha
LOCAL_SRC_FILES := fictional.cpp
include $(BUILD_SHARED_LIBRARY)
```

`LOCAL_MODULE = name` is also supported. Exactly one supported assignment must
occur in the block. `+=`, `?=`, `::=`, empty/quoted/dynamic values, or duplicate
assignments hold the name. Assignments to other `LOCAL_[A-Z0-9_]+` keys with these
recognized assignment operators are counted and discarded, including their
expression payloads; no validity or runtime semantics are asserted for them.
For example, `LOCAL_PATH := $(call my-dir)` is not evaluated or followed.

Recognized build markers are `BUILD_SHARED_LIBRARY`, `BUILD_STATIC_LIBRARY`,
`BUILD_EXECUTABLE`, `BUILD_PREBUILT`, `BUILD_JAVA_LIBRARY`, `BUILD_PACKAGE`,
`BUILD_HOST_EXECUTABLE`, `BUILD_HOST_SHARED_LIBRARY`,
`BUILD_HOST_STATIC_LIBRARY`, `BUILD_HOST_JAVA_LIBRARY`. These and `CLEAR_VARS`
are accepted only as `include $(NAME)` lines with surrounding ASCII spaces/tabs
and whitespace separating `include` from the marker. The marker itself is
literal, with no whitespace inside its parentheses. They are markers only,
not reads of Make's environment or filesystem. An unfinished block, new clear
marker before a build marker, or build marker without a clear marker adds
coverage. An incomplete known declaration is held.

Unescaped `#` starts a comment. Backslash-escaped `#` is retained as literal text,
which makes a module name unsupported. Odd trailing backslashes mark unsupported
continuations; their continuation-body lines are skipped rather than mistaken
for declarations. A continuation inside a block holds it. Unknown includes
(`include`, `-include`, `sinclude`) remain unfollowed and make scope uncertain;
inside a block they hold it. A tab-prefixed nonblank line is outside the subset.

Conditional/define/export/override directives, recipes and unrecognized statements
stop inspection of the remaining Make file, with coverage. No condition branch,
winning assignment, function, included file, implicit rule or build variant is
evaluated. The tool never sources Make, invokes a shell or starts a build.

## Requests and ambiguity

Requested names match exact known literal names across the selected files:

| State | Meaning |
| --- | --- |
| `observed_once` | One unheld literal declaration was observed. |
| `observed_multiple` | Multiple unheld declarations share the name; scope/variants were not resolved. |
| `observed_held` | At least one matching declaration is held for unsupported/ambiguous context. |
| `not_observed_selected_supported_scope` | No matching name was observed and selected parser scope has no unresolved identity/scope. |
| `held_incomplete_scope` | No matching name was observed, but unsupported syntax could conceal declarations. |

Neither unmatched state proves a missing real module. A declaration elsewhere,
generated declaration, alias or different name is outside the selected evidence.
Inputs are not a complete tree inventory. Known literal matches remain visible
even with other incomplete coverage; they do not establish effective build state.

## Bounds and output

The common file guards enforce 32 files including wanted text, 1 MiB/file,
4 MiB aggregate, 20,000 physical lines including final empty lines, 8,192
characters/line, UTF-8 optional BOM, and LF/CRLF. Bare CR, NUL and unsupported
controls are refused. BP tokens are capped at 40,000, nesting at 32, strings at
1,024 characters and identifiers at 256. Output declarations, findings, coverage,
repetition and requested-name collections are each capped at 4,000 entries.
JSON and HTML reports are at most 8 MiB each. No limit silently truncates output.

Top-level report fields:

- `schema_version`, `tool`, `scope`, `status`, `details_included` identify output.
- `sources` contains opaque ID, byte count, SHA-256 and explicitly selected
  parser label (`bp`, `mk`, `wanted`). Filenames/paths are omitted.
- `declarations` contains opaque ID, source ID, 1-based block-start line, syntax,
  `identity_known` and `held`. Details add `declared_name` (or null) and
  `module_kind`; discarded property values never appear.
- `repeated_names` contains opaque group IDs, declaration IDs and counts. Details
  add the known name. Groups are source-text observations, not resolved identities.
- `wanted` contains opaque request ID, state and matching declaration IDs.
  Details add the literal requested name.
- `unresolved_identity_or_scope` refers to build parsing, not every possible
  wanted-list issue; `ignored_make_rows` counts discarded non-module assignments.
- `findings` uses `REPEATED_DECLARED_NAME_OBSERVED` and/or
  `WANTED_NAME_NOT_OBSERVED` when applicable.
- `coverage_issues` contains fixed code, opaque source ID and physical line.
  Line zero marks an unterminated continuation at end of file. Unknown source
  text, discarded expressions, filenames and input paths are never emitted.

The report and its HTML rendering retain hashes, positions and structure even
when details are omitted. This is not anonymization. `MANIFEST.json` hashes only
the generated report files; it is unsigned and does not authenticate inputs or
establish rights to publish them. A report is limited to the documented subset,
not a claim of complete syntax validation or a successful Android build.
