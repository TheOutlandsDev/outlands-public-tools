# OUTLANDS | Bounding Box Contract Converter

Convert explicit pixel-edge and normalized box declarations exactly without clipping, rounding or updating assets. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game geometry metadata; no image assets.

Run from this complete tool directory:

```text
python -B boxes.py --input examples/input.json
python -B boxes.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original images, private programs, labels, accounts, models or datasets needed.

## Contract and interpretation

Library `boxes.check(raw_json_bytes)`. Input exactly `{format,images,boxes}`, format
`outlands-bounding-box-conversion-v1`. Box rows are the shared image-link fields plus
source and target: `{id,revision,image,image_revision,image_snapshot_sha256,source,target}`.
Source is exactly `{format,values}` with four values. Target is one of the same named
formats. Both selected lists must be nonempty and all image links must match exactly.

Supported formats:

| Name | Four values | Source value representation |
| --- | --- | --- |
| pixel-xyxy | left, top, right, bottom | Bounded integers |
| pixel-xywh | left, top, width, height | Bounded integers |
| unit-cxcywh | center-x/width, center-y/height, box-width/image-width, box-height/image-height | Exact unit-fraction strings |

Unit fractions are strings `n/d`: unsigned decimal integers, no leading zeros,
0<=n<=d, 1<=d<=1,000,000,000 and n<=1,000,000,000. No decimal strings, floats,
exponents, signs or whitespace. Fractions reduce canonically before snapshot pins
and identity accounting, so 2/8 and 1/4 are equivalent. Output normalized values use
the same reduced fraction syntax; pixel outputs use integers. Fractions avoid rounding.

Convert through exact rational pixel edges. Require positive width/height, all edges
inside [0,image-width] x [0,image-height], and integer pixel edges. A normalized center
inside the image can still yield outside edges. Normalized inputs resolving to
fractional pixel edges return NONINTEGRAL_PIXEL_EDGES instead of implicit rounding.
Pixel-xyxy uses half-open extent: width=right-left, never right-left+1.

For structurally qualified scope, report each box's exact pixel_edges as fraction
strings, valid flag, all failed criteria, target and converted_values. Invalid geometry
retains diagnostics but converted_values is null; valid peers still retain conversions.
Any such finding returns REVIEW_REQUIRED. Malformed rows, unknown/stale references
and conflicting identities instead withhold the whole assessment and scope pins.
coordinates_clipped/coordinates_rounded stay false. No rotated boxes, confidence,
object matching, polygon replacement, image rescaling, asset edits or dataset export.
The additional game-boxes.json fixture uses invented game-tile/hitbox declarations.

## Shared declarations, bounds and I/O

IDs match `[a-z][a-z0-9_-]{0,47}`. Revision integers are 1..1,000,000. SHA-256 strings
are exactly 64 lowercase hexadecimal characters. Image rows are exactly
`{id,revision,content_sha256,width,height}`, dimensions integers 1..1,000,000.
content_sha256 is supplied, never checked against an actual image. image_snapshot_sha256
instead hashes the full normalized image row, including dimensions and revision.

Taxonomy is `{id,revision,labels}`, 1..32 unique label IDs normalized by sorting.
Annotation rows are exactly `{id,revision,image,image_revision,image_snapshot_sha256,
label,taxonomy_sha256,kind,geometry}`. Kind is polygon/box. Polygon geometry is a list
of 3..128 two-integer [x,y] vertices without repeating the closing point. Box geometry
is `{left,top,right,bottom}`. There are at most 4,096 selected polygon vertices per
invocation, enforced before geometric analysis. No geometry strings are evaluated.

All pixel coordinates/extent source values are bounded integers -1,000,000..2,000,000,
allowing explicit out-of-frame declarations to be diagnosed. No booleans or numeric
string coercion. Origin is upper-left, x increases right, y down. Coordinates describe
pixel edges, not pixel-center indexes. Canvas boundaries at x=width/y=height are valid
edges. Box regions use [left,right) x [top,bottom). Values outside the declared frame
are geometry findings where analyzed, not silently clipped. Geometry syntax alone is
not geometric validity or alignment with actual image content.

Each identity-snapshot list is limited to 1,000 rows. Identical normalized snapshots
under one ID count once plus duplicate_rows. Conflicting ID groups withhold every
member, including repeated identical members within that group. Each list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Fixed issue codes use one-based logical row positions; row 0 is a cohort finding.
Rejected values are omitted. No latest revision or approval is selected implicitly.

Pins hash compact sorted-key escaped ASCII JSON plus LF; collections sort by ID.
Taxonomy labels, handoff selections and normalized fractions use their stated
normalization; polygon vertex order remains meaningful. input_sha256 hashes the exact
raw input bytes. Pins are consistency receipts, not signatures or authenticated evidence.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Malformed outer
schemas, taxonomy/handoff contracts, list limits and total vertex limits are fixed
refusals. Malformed identity rows/reference issues return REVIEW_REQUIRED with qualified
results withheld. Valid findings retain complete diagnostics as documented above.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default output is private stdout JSON. Optional
--out takes an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output: inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths and values. These guards do not sandbox hostile concurrent processes.

No network/provider/model calls, image decoding, asset reads, directory discovery,
training, dataset export, clock, command execution, URI/include following or environment
expansion. Only invented HVAC/game geometry metadata is included; no image assets.
Keep actual inputs/reports private. The tools are not anonymizers, rights checks or
independent truth/approval/privacy verifiers. See [origins](ORIGINS.md) and
[validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
