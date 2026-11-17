# Methodology and interpretation

## Four sequential selections

The caller selects receipt, source, explicit mapping and supplied preview. Each
ordinary single-link file is independently bounded to 4 MiB. The CLI does not
discover artifacts, read paths from content or apply the unused run_core manifest
helpers' 16-artifact/combined-total contract. Four per-role caps imply at most
16 MiB selected bytes, without an atomic combined snapshot guarantee.

Receipt declaration checks exact fields, symbolic ID, lowercase hashes, source
format/sheet selection and bounded actual integer count fields. Preview JSON uses
strict shared decoding. The public intake parser reruns on source/map bytes with
the receipt's explicit source format and sheet. Source or mapping refusal produces
a fixed error rather than a reconciliation result; invalid source rows can instead
produce an intake review preview with accounted rows and accepted unrelated records.

## Exact bytes, typed content and accounting

Source, map and supplied-preview raw SHA-256 values are checked separately.
The supplied JSON preview and complete recomputed preview are serialized as
canonical typed JSON and compared as bytes. Dictionary key order/whitespace do not
change that comparison, while array order, omitted/extra fields, accepted values,
provenance and Boolean-versus-integer types do. The report retains the supplied
raw preview hash and recomputed canonical hash, so semantically equal pretty JSON
can have different hashes when its receipt pin is current. Pretty map bytes change
the hash embedded in the recomputed preview. Receipt bytes receive a separate pin.

The receipt's declared input count must equal its four outcome categories, and
all five claims must equal observed counts. The tool really recomputes these
logical source-data-row counts: row_counts_recomputed is true. This is distinct
from selecting a complete source, authenticating a receipt, verifying actual
commits or inspecting store contents; none is established by count/hash agreement.

All mismatch diagnostics and intake review status globally hold readiness.
Observed counts and intake status remain available; there is no partial import
permission or guessed fallback. The summary omits accepted records and source-row
provenance as fields, while the independently supplied/recomputed previews include
them. Receipt IDs, metadata, fingerprints and coincidences remain private; omission
is not anonymization or authorization to disclose.

## Bounded conversion and workbook subset

Mappings explicitly declare field types, required values and one-to-four required
identity targets. Complete identical normalized records count once plus duplicates
and collect logical source-row positions. Different records at the same identity
withhold every valid group member. Invalid rows are separately accounted, and an
empty accepted set requires review. No implicit trimming/coercion is applied.
Text excludes ASCII C0+DEL, not every Unicode control. Optional empty is null;
integer zero, decimal signed zero and Boolean false remain distinct typed cases.

Integer/decimal bounds are 10^12 with at most six decimal fractional digits.
Default precision 28 exceeds the at-most-19 accepted significant digits, but the
implementation inherits Decimal context for abs/normalize. Qualification is
fresh-default-context only, without a universal context-independence promise.
Mapped dates are calendar-validated; an XLSX date-kind literal alone is not a
calendar validation unless its target map type requires it. Styles do not evaluate
formulas, infer units or convert spreadsheet date serials.

XLSX input ZIP members are bounded and decompressed in memory, not extracted to
filesystem paths. Every bound sheet is checked, including unselected ones. Narrow
relationship/worksheet/cell controls refuse active/hidden, external, macro and
unsupported features. Accepted opaque property/style parts are bounded rather
than completely interpreted. This is not an OOXML/Office/rendering conformance test.

## Independent evidence and limits

The guide authors raw source/map/receipt bytes, complete expected typed previews
and complete expected summary reports. Hashing authored bytes is not a matching
oracle. It never calls intake preview/mapping or receipt reconciliation to create
expected values. Actual script entry points exercise the product and generator;
manual inline/shared fixtures do not establish independent public-writer interchange.
Both early semantic/prose reviews precede formal execution. Every prior input,
report and other artifact remains byte-identical after every case, and a complete
manifest is independently reconstructed. A separate five-byte controlled write
failure is not counted as an actual CLI entry-point check.

JSON/CSV/ZIP byte caps and Python-character/structure limits are cooperative
application limits, not OS resource isolation. XML accumulated text/attribute
budgets use characters, expanded ZIP budgets bytes. Fresh outputs refuse reuse
and source destinations, but failures may retain unconfirmed partial files.
Trusted quiescent inputs/parents and sequential sampled stability checks do not
prove atomic snapshots, hostile-writer containment, rollback, full metadata
preservation or hardware durability. No production import or actual run is performed.
