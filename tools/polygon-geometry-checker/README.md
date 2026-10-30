# OUTLANDS | Polygon Geometry Checker

Inspect explicitly supplied simple polygons using bounded exact integer arithmetic without repairing geometry or reading images. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game geometry metadata; no image assets.

Run from this complete tool directory:

```text
python -B polygons.py --input examples/input.json
python -B polygons.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original images, private programs, labels, accounts, models or datasets needed.

## Contract and interpretation

Library `polygons.check(raw_json_bytes)`. Input exactly `{format,images,polygons}`,
format `outlands-polygon-geometry-v1`. Polygon rows are the shared image-link fields
plus vertices: `{id,revision,image,image_revision,image_snapshot_sha256,vertices}`.
Selected images and polygons must be nonempty; image links must match exactly.
Malformed rows, unknown/stale references or conflicting identities withhold the whole
assessment and all qualified scope pins. Ordered vertices are never normalized by
rotation, winding, closing-point removal, clipping, hull selection or simplification.

Analyze each syntactically valid ring for vertices outside the declared canvas,
repeated vertices, zero-length edges, zero signed area and edge contacts inconsistent
with a simple polygon. Nonadjacent edge crossings, endpoint touches and collinear
overlaps are findings. Adjacent edges may share their one ring endpoint but may not
backtrack over one another. Collinear vertices that continue along a boundary are
allowed. Either winding is allowed. Explicitly repeating the first vertex at the end
is not silently removed; it produces repeated-vertex/zero-edge findings.

Report valid flag, all failed criterion codes, vertex count, twice-signed area, exact
absolute area as a rational, orientation and axis-aligned envelope. With x right/y
down, positive shoelace area is clockwise. Zero area has degenerate orientation.
Area/envelope remain diagnostic for invalid rings, not a valid region measurement.
Count all edge contacts but retain only the first 16 edge-pair details, with explicit
truncation flag. Edge indices are zero-based; issue row positions are one-based.

Valid geometry findings return REVIEW_REQUIRED and retain the complete assessment
and declaration pins. Eligibility is only for manual geometry review. The envelope is
not a replacement for a concave polygon or evidence of object extent. No holes,
multiple rings, curves, masks, rasterization, transformations, repair or pixel access.
geometry_repaired and content_geometry_alignment_verified remain false.

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
