"""Exercise installed annotation packages using embedded fictional declarations."""
from __future__ import annotations

import json
from importlib.resources import files

from outlands_annotation_manifest_checker.manifest import check as manifest_check
from outlands_polygon_geometry_checker.polygons import check as polygon_check
from outlands_bounding_box_converter.boxes import check as box_check
from outlands_annotation_export_handoff_checker.handoff import check as handoff_check

PACKAGES = (
    "outlands_annotation_manifest_checker",
    "outlands_polygon_geometry_checker",
    "outlands_bounding_box_converter",
    "outlands_annotation_export_handoff_checker",
)
CHECKS = (manifest_check, polygon_check, box_check, handoff_check)


def sample(index: int, name: str = "input.json") -> bytes:
    return files(PACKAGES[index]).joinpath("examples", name).read_bytes()


def main() -> None:
    values = [json.loads(sample(index)) for index in range(4)]
    reports = [check(sample(index)) for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "PASS" for report in reports)
    manifest, polygon, box, handoff = reports
    assert values[0]["taxonomy"] == values[3]["taxonomy"]
    assert values[0]["images"] == values[3]["images"]
    assert values[0]["annotations"] == values[3]["annotations"]
    assert values[1]["images"] == values[2]["images"] == values[0]["images"][:1]
    assert values[1]["polygons"][0]["vertices"] == values[0]["annotations"][0]["geometry"]
    assert values[2]["boxes"][0]["source"]["values"] == [10, 10, 50, 30]
    assert manifest["taxonomy_sha256"] == handoff["taxonomy_sha256"]
    assert manifest["images_sha256"] == handoff["images_sha256"]
    assert manifest["annotations_sha256"] == handoff["annotations_sha256"]
    assert manifest["assessment"]["unannotated_images"] == []
    assert polygon["assessment"]["valid_polygons"] == 1
    assert box["assessment"]["all_boxes_converted"] is True
    assert handoff["assessment"]["eligible_for_manual_export_review"] is True
    assert handoff["dataset_export_performed"] is False
    assert all(report["artifact_bytes_verified"] is False for report in reports)
    reviews = [check(sample(index, "needs-review.json"))
               for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "REVIEW_REQUIRED" for report in reviews)
    print(json.dumps({"status": "PASS", "positive_examples": 4,
                      "review_examples": 4, "shared_pins": "PASS",
                      "artifact_bytes_verified": False,
                      "dataset_export_performed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
