# OUTLANDS | Annotation Export Handoff Checker

Reconcile pinned annotation selections, category mappings, approval declarations and expected export counts without exporting assets. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game geometry metadata; no image assets.

Run from this complete tool directory:

```text
python -B handoff.py --input examples/input.json
python -B handoff.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original images, private programs, labels, accounts, models or datasets needed.

## Contract and interpretation

Library `handoff.check(raw_json_bytes)`. Input exactly
`{format,taxonomy,images,annotations,categories,approvals,handoff}`, format
`outlands-annotation-export-handoff-v1`. Images/annotations use the shared schemas.
Category rows are `{id,label,index}`, index integer 0..255. Every taxonomy label needs
exactly one mapping; distinct mapping IDs for a label or reused index are ambiguous.
Sparse indexes are allowed. This is a generic category contract, not COCO/YOLO or any
external format compatibility claim.

Approval rows are `{id,annotation,annotation_revision,annotation_sha256,decision}`,
decision approve/reject. Revision/hash must match the complete normalized annotation,
including ordered geometry, label, taxonomy pin and image snapshot pin. Different
approval IDs for one annotation are ambiguous even when decisions match. All approvals
are reference-validated, including unused ones. Approval declarations are not authenticated.

Handoff is exactly `{id,revision,images_sha256,annotations_sha256,taxonomy_sha256,
categories_sha256,selected_annotations,expected_images,expected_annotations,
expected_label_counts}`. All four scope pins must match the actual complete normalized
collections, including unselected sources. Selected_annotations is 1..1,000 unique
annotation IDs, normalized by sorting; duplicates refuse rather than double count.
Expected image/annotation counts are integers 1..1,000. Expected_label_counts has
exactly all taxonomy labels with integer counts 0..1,000, including zero counts.

Malformed/conflicting rows, ambiguous mapping/approval slots, unknown selections or
stale/unknown references/scope pins withhold the whole assessment and qualified pins.
For qualified scope, reconcile selected annotations and their distinct referenced
images against every expected count and label count; require one approve decision per
selected annotation. Missing/rejected approvals and count mismatches return
REVIEW_REQUIRED with complete actual counts, missing/rejected IDs and failed criteria.
Unused valid reject decisions do not reject a different selected annotation.

Only if all criteria pass is eligible_for_manual_export_review true and
selected_annotations_sha256 issued for full selected snapshots sorted by ID. Otherwise
the selected pin is null. No dataset/image/label files are exported. geometry_verified,
content_geometry_alignment_verified, approval_authenticity_verified and
dataset_export_performed stay false. Reference consistency and declared approvals do
not prove simple polygons, meaningful labels, correct object boundaries, rights or
permission to export. Geometry review remains a separate explicit step.

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
