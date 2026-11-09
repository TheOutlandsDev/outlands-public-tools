# Annotation and geometry review

These four tools check supplied declarations in a fictional, bounded
image-annotation workflow. They operate on JSON records and never open image
assets. Each input has its own exact schema and normalized SHA-256 pins. A pin
identifies a declared snapshot; it is not a signature or proof that image bytes
or labels are correct.

1. **Manifest:** list declared images, taxonomy labels and annotations.
   The checker validates references, revisions and normalized pins. It reports
   unannotated images and label counts. It checks geometry syntax, not geometric
   validity.
2. **Polygon:** select image declarations and ordered vertices. The checker
   uses exact integer arithmetic to report area, orientation, envelope,
   out-of-frame vertices and non-simple edge contacts. It does not repair or
   align a polygon to pixels.
3. **Box conversion:** select an image and an explicitly named source and
   target convention. Pixel-edge and unit-fraction values convert exactly.
   The checker neither rounds nor clips coordinates.
4. **Handoff:** select pinned annotations, category mappings, declared approval
   decisions and expected counts. The checker tests internal consistency and
   eligibility for manual export review. No approval is authenticated and no
   dataset is exported.

A source `PASS` means only that the selected JSON records meet that tool's
contract. `REVIEW_REQUIRED` identifies declared inconsistencies or findings.
It is possible for a manifest to PASS while its polygon geometry needs review;
the checks answer different questions. The handoff does not upgrade a polygon
finding into geometric validity. Image dimensions, hashes, taxonomy and approvals
are supplied assertions. No external annotation format, model, browser or
application adapter is verified.

IDs and hashes can reveal project structure even when raw image bytes are
absent. Use fictional examples for public tests, and keep actual inputs and
reports in private, trusted storage. The package release includes generic
public source and those fictional examples only.
