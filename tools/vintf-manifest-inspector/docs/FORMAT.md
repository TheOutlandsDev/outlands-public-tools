# Supported VINTF declaration subset

Inputs are UTF-8 (optional BOM), LF/CRLF, at most 1 MiB each / 4 MiB total / 32
selected current+before files. Text controls, bare CR, NUL, more than 20,000
physical lines or 8,192 characters per line are refused. The optional XML 1.0 declaration must be first, with literal version, optional
UTF-8/UTF8 encoding and optional yes/no standalone in that order. DTD/entity declaration
markers are conservatively rejected even inside otherwise inert comments.

The original restricted reader bounds tree construction before accepting extra
nodes/attributes: 8,000 elements/file, depth 32, 16
attributes/element, 256-character attribute names, 1,024-character attribute
values and 8,192-character text/tail nodes. Malformed XML or a bound refuses the
entire run. Comments are ignored; processing instructions require coverage.
No external entity/include/schema/resource is resolved or fetched. There is no
Expat, ElementTree, SAX or other native XML-parser call in this tool. ASCII names,
balanced tags, quoted attributes and comment syntax form the supported subset;
CDATA and other declarations/markup are refused. Duplicate attributes,
unbalanced/multiple roots and unknown/malformed references are refused.
Predefined amp/lt/gt/apos/quot and valid bounded decimal/lowercase-x hexadecimal
numeric references are decoded once. Encoded controls/noncharacters outside the
supported character subset are refused. Literal attribute tab/newline whitespace
is normalized before reference decoding. XML declaration values cannot use
references. Unicode element/attribute names and general XML compatibility are
outside this edition.

Namespace declarations/prefixed names anywhere make the selected file unsupported
coverage without interpreting its HALs. Root must be unnamespaced manifest with version 1.0/2.0 and device/framework
type. target-level is accepted as out-of-scope root metadata; it is not used to
evaluate compatibility. Other root attributes/elements require coverage. XML
element positions are preorder ordinals excluding comments, not source lines.

HAL format is hidl by default, or explicit aidl. Native/unknown formats are
unsupported. Modifiers including override, min/max levels and APEX attributes
require coverage and are not evaluated as a winning declaration or disabled HAL.
Package names are ASCII dot-separated identifiers, at most 256 characters;
interface identifiers and supported literal instance strings are at most 128.
Unknown nested elements/attributes and mixed container text require coverage.

HIDL declarations support explicit major.minor versions with each number 0–99,
interface/name/instance combinations, and fqname @version::Interface/instance.
Fqname carries its own version independent of version elements. Interface-form
instances require explicit versions. Supported transports are hwbinder, or
passthrough with arch 32/64/32+64. Unknown transport/arch data is coverage and is
not copied into normalized fields. Versions of the same major in one HAL and
repeated versions are review signals; this is not complete cross-file validation.

AIDL requires meta-version 2.0 and exactly one explicit decimal version 1–9999
in this subset. Inferred defaults from platform/version context are deliberately
not used. Interface-form and fqname Interface/instance declarations are supported.
AIDL transport declarations remain uninspected coverage. Regex instances and
other full-platform grammar are not interpreted.

Comparison keys include manifest type, format, package, version, interface and
instance. Device/framework keys remain separate. Version or identity changes
produce removal/addition; supported transport/arch changes produce changed
records. Duplicate keys on either side are ambiguous and never arbitrarily
paired. Their selected declaration records remain available for private review.
No effective manifest order, override application, APEX/property selection,
compatibility matrix, root metadata diff or runtime service availability is
inferred. Partial supported results coexist with explicit coverage issues.

Schema version 1 includes inputs, declarations, hal_elements_observed, changes,
ambiguous_comparisons, findings, coverage_issues, comparison scope and status.
IDs are local to report/input order. Details opt-in adds only supported normalized
fields; raw XML, comments, unknown scalar values and local filenames are omitted.
