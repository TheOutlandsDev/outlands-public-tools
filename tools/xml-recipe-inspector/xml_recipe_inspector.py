#!/usr/bin/env python3
"""Bounded structural summaries of an owner-provided, unnamespaced recipe XML.

Adapted from the owner's small stdlib inspector. No recipe data is bundled.
Licensing is unassigned; no vendor validation is asserted.
"""
import argparse
import csv
import io
import json
import math
import os
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET
from xml.parsers import expat

MAX_INPUT_BYTES = 1024 * 1024
MAX_DEPTH = 64
MAX_ELEMENTS = 20_000
MAX_TEXT_CHARS = 1024 * 1024
MAX_FIELD_CHARS = 2048
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
OVERLAY_FIELDS = (
    "id", "image_id", "orientation", "nominal_value_um", "pp1_mid_x", "pp1_mid_y",
    "pp2_mid_x", "pp2_mid_y", "delta_mid_x_px", "delta_mid_y_px",
    "delta_mid_x_um", "delta_mid_y_um",
)


class RecipeError(Exception):
    """Fixed error codes, without recipe text, filenames or parser excerpts."""


def require(condition, code):
    if not condition:
        raise RecipeError(code)


def _absolute(path):
    p = Path(path)
    require(".." not in p.parts, "PARENT_TRAVERSAL_FORBIDDEN")
    return p if p.is_absolute() else Path.cwd() / p


def _check_ancestors(path):
    for p in [path, *path.parents]:
        require(not stat.S_ISLNK(p.lstat().st_mode), "SYMLINK_FORBIDDEN")


def read_xml(path):
    require(hasattr(os, "O_NOFOLLOW"), "PLATFORM_UNSUPPORTED")
    p = _absolute(path)
    _check_ancestors(p)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), "INPUT_NOT_REGULAR")
        require(0 < before.st_size <= MAX_INPUT_BYTES, "INPUT_SIZE_LIMIT")
        chunks, count = [], 0
        while True:
            chunk = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            require(count <= MAX_INPUT_BYTES, "INPUT_SIZE_LIMIT")
        after = os.fstat(fd)
        for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"):
            require(getattr(before, field) == getattr(after, field), "INPUT_CHANGED")
        require(count == before.st_size, "INPUT_CHANGED")
        return b"".join(chunks)
    finally:
        os.close(fd)


def parse_xml(data):
    require(type(data) is bytes and 0 < len(data) <= MAX_INPUT_BYTES, "INPUT_SIZE_LIMIT")
    builder = ET.TreeBuilder()
    parser = expat.ParserCreate()
    depth = count = text_chars = 0

    def start(name, attrs):
        nonlocal depth, count
        depth += 1
        count += 1
        require(depth <= MAX_DEPTH, "XML_DEPTH_LIMIT")
        require(count <= MAX_ELEMENTS, "XML_ELEMENT_LIMIT")
        require(":" not in name and not any(k == "xmlns" or k.startswith("xmlns:") for k in attrs),
                "XML_NAMESPACE_UNSUPPORTED")
        builder.start(name, attrs)

    def end(name):
        nonlocal depth
        builder.end(name)
        depth -= 1

    def text(value):
        nonlocal text_chars
        text_chars += len(value)
        require(text_chars <= MAX_TEXT_CHARS, "XML_TEXT_LIMIT")
        builder.data(value)

    def forbidden(*args):
        raise RecipeError("XML_DECLARATION_FORBIDDEN")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.ProcessingInstructionHandler = forbidden
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse(data, True)
        require(depth == 0, "XML_MALFORMED")
        return builder.close()
    except (expat.ExpatError, ET.ParseError, ValueError):
        raise RecipeError("XML_MALFORMED") from None


def field(element, path):
    value = element.findtext(path)
    if value is None:
        return None
    value = value.strip()
    require(len(value) <= MAX_FIELD_CHARS, "FIELD_SIZE_LIMIT")
    return value


def number(value, optional=False):
    if optional and (value is None or value == ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise RecipeError("INVALID_NUMBER") from None
    require(math.isfinite(result), "NONFINITE_NUMBER")
    return result


def finite_result(value):
    require(math.isfinite(value), "NUMERIC_OVERFLOW")
    return value


def inspect_xml(data):
    root = parse_xml(data)
    # Preserve the original inspector's first-descendant PixelSize/X convention.
    pixel_size = number(field(root, ".//PixelSize/X"))
    require(pixel_size > 0, "INVALID_PIXEL_SIZE")
    modules = []
    for module in root.findall("./Modules/Module"):
        image = module.find("./GeometryImages/GeometryImage")
        row = {"module_id": field(module, "ID"), "image_id": None, "location": None,
               "origin_x": None, "origin_y": None, "pixel_size_x_um": None, "pixel_size_y_um": None}
        if image is not None:
            row.update(image_id=field(image, "ImageID"), location=field(image, "Location"))
            for key, path in (("origin_x", "Origin/X"), ("origin_y", "Origin/Y"),
                              ("pixel_size_x_um", "PixelSize/X"), ("pixel_size_y_um", "PixelSize/Y")):
                row[key] = number(field(image, path), optional=True)
        modules.append(row)

    measurements = []
    for measurement in root.findall("./Measurements/Measurement"):
        row = {key: field(measurement, path) for key, path in (
            ("id", "ID"), ("type", "Type"), ("image_id", "ImageID"), ("orientation", "Orientation"),
            ("direction", "Direction"), ("nominal_value_um", "NominalValue"),
            ("nominal_value_second", "NominalValueSecond"))}
        properties = measurement.findall("./PointProperty")
        row.update(point_property_count=len(properties), point_properties=[])
        for index, prop in enumerate(properties):
            def points(path):
                return [(number(field(point, "X")), number(field(point, "Y")))
                        for point in prop.findall(path)]
            user_points, algo_points = points("./UserPoints/Point"), points("./AlgoPoints/Point")
            info = {"index": index, "user_points": user_points, "algo_points": algo_points,
                    "edge_factor_1": field(prop, "EdgeFactor1"), "edge_factor_2": field(prop, "EdgeFactor2"),
                    "enable_gl_edge": field(prop, "EnableGLEdge")}
            if len(user_points) == 2:
                (x1, y1), (x2, y2) = user_points
                dx, dy = finite_result(x2 - x1), finite_result(y2 - y1)
                length = finite_result(math.hypot(dx, dy))
                info.update(user_midpoint_x=finite_result(x1 / 2 + x2 / 2),
                            user_midpoint_y=finite_result(y1 / 2 + y2 / 2),
                            delta_x_px=dx, delta_y_px=dy, length_px=length,
                            length_um_from_pixels=finite_result(length * pixel_size))
            row["point_properties"].append(info)
        measurements.append(row)

    overlays = []
    for measurement in measurements:
        if measurement["type"] != "OVL_LN_LN" or len(measurement["point_properties"]) < 2:
            continue
        p1, p2 = measurement["point_properties"][:2]
        nominal = measurement["nominal_value_um"]
        item = dict.fromkeys(OVERLAY_FIELDS)
        item.update(id=measurement["id"], image_id=measurement["image_id"],
                    orientation=measurement["orientation"],
                    nominal_value_um=None if nominal in (None, "", "NaN") else number(nominal),
                    pp1_mid_x=p1.get("user_midpoint_x"), pp1_mid_y=p1.get("user_midpoint_y"),
                    pp2_mid_x=p2.get("user_midpoint_x"), pp2_mid_y=p2.get("user_midpoint_y"))
        if "user_midpoint_x" in p1 and "user_midpoint_x" in p2:
            dx = finite_result(p2["user_midpoint_x"] - p1["user_midpoint_x"])
            dy = finite_result(p2["user_midpoint_y"] - p1["user_midpoint_y"])
            item.update(delta_mid_x_px=dx, delta_mid_y_px=dy,
                        delta_mid_x_um=finite_result(dx * pixel_size),
                        delta_mid_y_um=finite_result(dy * pixel_size))
        overlays.append(item)
    return pixel_size, modules, measurements, overlays


def parse_recipe(xml_path):
    return inspect_xml(read_xml(xml_path))


def csv_cell(value):
    if isinstance(value, str) and value.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def render_outputs(modules, measurements, overlays):
    outputs = {}
    for name, value in (("modules_summary.json", modules), ("measurements_summary.json", measurements),
                        ("overlay_line_line_summary.json", overlays)):
        outputs[name] = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        require(sum(map(len, outputs.values())) <= MAX_OUTPUT_BYTES, "OUTPUT_SIZE_LIMIT")
    if overlays:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=OVERLAY_FIELDS)
        writer.writeheader()
        for row in overlays:
            writer.writerow({key: csv_cell(row.get(key)) for key in OVERLAY_FIELDS})
        outputs["overlay_line_line_summary.csv"] = stream.getvalue().encode("utf-8")
        require(sum(map(len, outputs.values())) <= MAX_OUTPUT_BYTES, "OUTPUT_SIZE_LIMIT")
    return outputs


def write_outputs(out_dir, outputs):
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
            and os.open in os.supports_dir_fd, "PLATFORM_UNSUPPORTED")
    allowed = {"modules_summary.json", "measurements_summary.json", "overlay_line_line_summary.json",
               "overlay_line_line_summary.csv"}
    require(type(outputs) is dict and bool(outputs) and set(outputs) <= allowed
            and all(type(value) is bytes for value in outputs.values())
            and sum(map(len, outputs.values())) <= MAX_OUTPUT_BYTES, "INVALID_OUTPUT")
    path = _absolute(out_dir)
    _check_ancestors(path.parent)
    try:
        os.mkdir(path, 0o700)  # Existing directories/files/symlinks are always refused.
    except FileExistsError:
        raise RecipeError("OUTPUT_EXISTS") from None
    directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, payload in outputs.items():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            with os.fdopen(fd, "wb") as target:
                target.write(payload)
                target.flush()
                os.fsync(target.fileno())
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def main(argv=None):
    try:
        parser = _Parser(prog="xml_recipe_inspector.py", description="Inspect recipe structure; no vendor measurement validation.")
        parser.add_argument("xml_path", type=Path)
        parser.add_argument("--out-dir", required=True, type=Path, help="New private output directory; parent must exist.")
        args = parser.parse_args(argv)
        _, modules, measurements, overlays = parse_recipe(args.xml_path)
        outputs = render_outputs(modules, measurements, overlays)
        write_outputs(args.out_dir, outputs)
        print(json.dumps({"status": "ok", "modules": len(modules), "measurements": len(measurements),
                          "overlay_rows": len(overlays), "files_written": len(outputs)}, sort_keys=True))
        return 0
    except RecipeError as error:
        print(json.dumps({"status": "error", "code": str(error)}, sort_keys=True), file=sys.stderr)
    except (OSError, ValueError, OverflowError):
        print('{"status":"error","code":"IO_OR_ENCODING_ERROR"}', file=sys.stderr)
    return 2


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RecipeError("ARGUMENTS_INVALID")


if __name__ == "__main__":
    sys.exit(main())
