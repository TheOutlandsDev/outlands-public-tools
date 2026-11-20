"""Report external workbook references and worksheet error tokens without opening Excel."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from xml.etree import ElementTree
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile
from zlib import error as CompressionError


MAX_WORKBOOK_BYTES = 25 * 1024 * 1024
MAX_ZIP_MEMBERS = 2_000
MAX_ZIP_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024
FORMULA_ERROR_TOKENS = (b"#REF!", b"#DIV/0!", b"#VALUE!", b"#NAME?", b"#NUM!", b"#NULL!")
REQUIRED_PARTS = {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"}
WORKBOOK_REFERENCE = re.compile(r"\[([^\]]+\.(?:xls|xlsx|xlsm))\]", re.IGNORECASE)
XML_DECLARATION = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


class WorkbookError(ValueError):
    """A workbook cannot be safely inspected."""


@dataclass(frozen=True)
class WorkbookInspection:
    external_link_count: int
    formula_error_count: int


def _members(archive: ZipFile) -> set[str]:
    members = archive.infolist()
    if len(members) > MAX_ZIP_MEMBERS:
        raise WorkbookError("The workbook archive contains too many members")
    if sum(member.file_size for member in members) > MAX_ZIP_UNCOMPRESSED_BYTES:
        raise WorkbookError("The workbook archive expands beyond the size limit")

    files: set[str] = set()
    seen: set[str] = set()
    for member in members:
        name = member.orig_filename
        normalized = name.removesuffix("/")
        path = PurePosixPath(normalized)
        if (name != member.filename or path.is_absolute() or ".." in path.parts
                or path.as_posix() != normalized or "\\" in name or ":" in name):
            raise WorkbookError("The workbook archive contains an unsafe member path")
        key = normalized.casefold()
        if key in seen:
            raise WorkbookError("The workbook archive contains a duplicate member")
        seen.add(key)
        mode = member.external_attr >> 16
        if (member.create_system == 3 and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
                or member.flag_bits & 1 or member.compress_type not in (ZIP_STORED, ZIP_DEFLATED)):
            raise WorkbookError("The workbook archive contains an unsupported member")
        if member.is_dir():
            continue
        if key.endswith("vbaproject.bin") or key.startswith("xl/macrosheets/"):
            raise WorkbookError("Macro-enabled workbook content is not accepted")
        files.add(name)
    if not REQUIRED_PARTS <= files:
        raise WorkbookError("The ZIP is missing required XLSX parts")
    return files


def _read_xml_part(archive: ZipFile, name: str) -> tuple[ElementTree.Element, bytes]:
    member = archive.getinfo(name)
    if member.file_size > MAX_XML_BYTES:
        raise WorkbookError("An inspected XML part exceeds the size limit")
    data = archive.read(member)
    text = data.decode("utf-8-sig")
    if XML_DECLARATION.search(text):
        raise WorkbookError("XML document types and entities are not accepted")
    return ElementTree.fromstring(text), data


def inspect_workbook(content: bytes) -> WorkbookInspection:
    if not content or len(content) > MAX_WORKBOOK_BYTES:
        raise WorkbookError("The workbook is empty or exceeds the 25 MiB input limit")
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = _members(archive)
            types, _ = _read_xml_part(archive, "[Content_Types].xml")
            if any("macroenabled" in item.get("ContentType", "").casefold() for item in types):
                raise WorkbookError("Macro-enabled workbook content is not accepted")
            external_parts = sum(name.startswith("xl/externalLinks/") and name.endswith(".xml") for name in names)
            references: set[str] = set()
            formula_errors = 0
            for name in names:
                relationships = name.endswith(".rels")
                worksheet = name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
                if not (relationships or worksheet):
                    continue
                root, data = _read_xml_part(archive, name)
                if worksheet:
                    formula_errors += sum(data.count(token) for token in FORMULA_ERROR_TOKENS)
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    if relationships and local_name == "Relationship":
                        target = element.get("Target", "").strip()
                        if target and ("externallink" in name.lower()
                                       or target.lower().endswith((".xls", ".xlsx", ".xlsm"))):
                            references.add(target)
                    elif worksheet and local_name == "f":
                        references.update(ref.strip() for ref in WORKBOOK_REFERENCE.findall(element.text or ""))
            return WorkbookInspection(max(external_parts, len(references)), formula_errors)
    except WorkbookError:
        raise
    except (BadZipFile, CompressionError, ElementTree.ParseError, UnicodeError, OSError, RuntimeError) as exc:
        raise WorkbookError("The input is not a readable XLSX workbook") from exc


def _ordinary_file(info: os.stat_result) -> bool:
    attrs = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _load_workbook(path: Path) -> bytes:
    selected = path.lstat()
    if not _ordinary_file(selected):
        raise WorkbookError("The input must be an ordinary workbook file")
    if selected.st_size > MAX_WORKBOOK_BYTES:
        raise WorkbookError("The workbook exceeds the 25 MiB input limit")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
            raise WorkbookError("The input workbook changed while opening")
        return stream.read(MAX_WORKBOOK_BYTES + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_workbook(_load_workbook(args.workbook))
    except WorkbookError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("The workbook could not be read", file=sys.stderr)
        return 2
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
