# JSON report version 1

The CLI writes UTF-8 JSON with a final newline. All comparisons use ordinal, case-sensitive identity matching and sorted declaration keys. The schema is deliberately descriptive: `before` and `after` values are canonical JSON arrays encoded as strings. Consumers must decode those strings as JSON, not split them on punctuation.

Top-level fields:

| Field | Meaning |
| --- | --- |
| `schemaVersion` | Integer `1`. |
| `scope` | `public-declarations-only`. |
| `beforeAssembly`, `afterAssembly` | Assembly simple names; they must match. Versions, cultures and strong names are excluded. |
| `beforeSha256`, `afterSha256` | Lowercase SHA-256 of the actual immutable input byte snapshots. These hashes identify bytes, not authenticity. |
| `beforeDeclarations`, `afterDeclarations` | Number of supported public declarations observed. |
| `changes` | Sorted array of `{kind, id, before, after}`. Kind is `added`, `removed`, or `changed`. A missing side is JSON `null`. |

There are no timestamps or filesystem paths in the report wrapper. JSON escaping is normal and significant: for example, a plus sign in a nested type may appear as `\u002B`. Decode JSON rather than comparing rendered text.

## Identities and compared values

Each `id` is itself an unambiguous JSON array encoded as a string:

| Kind | Identity tuple | Compared value array |
| --- | --- | --- |
| Type | `["type", fullName]` | Type attributes integer, base type, sorted interfaces, generic description string. |
| Method/constructor | `["method", type, name, genericArity, parameterTypes]` | Return type, signature header byte, required parameter count, method attributes integer, generic description string. |
| Field | `["field", type, name]` | Field type, field attributes integer. |
| Property | `["property", type, name, indexParameterTypes]` | Property type, signature header, attributes integer, public getter presence, public setter presence. |
| Event | `["event", type, name]` | Event type, attributes integer, public add/remove/raise presence. |

Generic descriptions encode parameter index, attributes, and sorted constraint types. Generic parameter names do not affect comparison. Referenced named types include the referenced assembly simple name, for example `[System.Runtime]System.IDisposable`. Own nested types use `Namespace.Outer+Inner`. Type definition visibility checks follow the enclosing chain.

Named type components support Unicode letters/digits, underscore, and the generic arity backtick; namespace components additionally support dots but not backticks. Other characters produce a coverage error. Referenced assembly/module simple names cannot contain brackets or a colon. Nested type/reference namespace fields must be empty. These deliberate restrictions prevent delimiter-bearing legal metadata names from aliasing the canonical display identity; unusual identifiers from some languages or hand-authored IL are outside this initial scope. Method/field/property/event names are JSON tuple fields and are not split on punctuation.

Accessor methods appear separately from their property/event declaration. This makes a setter's removal visible both in accessor presence and the public method surface; it is intentional. Interface changes affect the type entry. Attributes are raw declaration flags, including compiler-generated flag differences such as `BeforeFieldInit`; investigate a finding before treating it as a breaking change.

Signatures preserve class/value-type tags, generic type `!0` and method `!!0` parameter positions, by-reference/pointer modifiers, SZ arrays, multidimensional rank/sizes/lower bounds, function pointer signatures, calling convention bytes, and `modreq`/`modopt`. Unknown/malformed elements, trailing bytes, ambiguous public identities, or exceeded limits are errors, not partial results. This decoder covers the documented CLI signature forms used in the authored tests; it is not a verifier for all possible CLI images.

## Explicit exclusions

The tool does not compare execution, IL, resources, initializers, dependency resolution, or runtime compatibility. It excludes protected/internal/private members, type forwarders, assembly version/culture/public-key identity, custom attributes and annotations (including nullability and platform support), parameter names/default values/attributes (`ref` versus `out` can compare equal), constant values (including enum members), generic parameter names, packing/layout offsets, field initializers, marshaling, security declarations, method implementation flags, extension-method annotations, and source language semantics. Adding an optional argument or changing an enum constant can be meaningful while producing no supported-declaration change.

Changing compiler/framework versions can change reference scopes or flags. Compare consistent build targets when practical. Distinct assembly simple names are refused to avoid accidentally comparing unrelated projects; equal simple names alone do not establish full assembly identity.

## Fixed processing bounds

| Resource | Maximum |
| --- | --- |
| Input assembly | 32 MiB each; two sequential snapshots. |
| Rows in any metadata table | 100,000. |
| Public declarations | 50,000 per assembly. |
| Signature blob | 16,384 bytes. |
| Type/signature nesting | 32 recursive levels (depth greater than 32 fails). |
| Signature elements, interface/constraint/generic counts | 1,024 each. |
| Metadata name | 1,024 UTF-16 code units; control characters refused. |
| Decoded signature / identity / declaration value | 65,536 UTF-16 code units each. |
| Total canonical identity/value characters | 8 Mi per assembly. |
| Type/signature decoding visits | 2,000,000 per assembly. |

These bounds apply to this tool's processing and output. They do not harden the underlying metadata reader against malicious native-level inputs. No timeout, process isolation, or security sandbox is provided. Only trusted build files belong in this workflow.
