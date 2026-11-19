"""Validate a saved external-link registry without contacting its destinations."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import TextIO
import unicodedata
from urllib.parse import parse_qsl, urlsplit


MAX_LINKS = 1024
MAX_INPUT_BYTES = 256 * 1024
_SESSION_KEYS = frozenset({"ticket", "token", "access_token", "session", "sessionid"})
_BAD_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_BRACKETED_AUTHORITY = re.compile(r"\[([^\[\]]+)\](?::[0-9]+)?")
_PLAIN_AUTHORITY = re.compile(r"([^:\[\]]+)(?::[0-9]+)?")
_HOST_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


class ExternalLinkContractError(ValueError):
    """A registry rule was violated. Messages contain only fixed text."""


@dataclass(frozen=True, slots=True)
class ExternalLink:
    label: str
    href: str


def _unsafe_character(char: str) -> bool:
    return unicodedata.category(char) in {"Cc", "Cf", "Cs"}


def _check_authority(authority: str) -> None:
    if authority.startswith("["):
        match = _BRACKETED_AUTHORITY.fullmatch(authority)
        if match is None or "%" in match[1]:
            raise ValueError
        IPv6Address(match[1])
        return

    match = _PLAIN_AUTHORITY.fullmatch(authority)
    if match is None:
        raise ValueError
    hostname = match[1].encode("idna").decode("ascii").removesuffix(".")
    if not hostname or len(hostname) > 253:
        raise ValueError
    if all(char in "0123456789." for char in hostname):
        IPv4Address(hostname)
    elif any(_HOST_LABEL.fullmatch(part) is None for part in hostname.split(".")):
        raise ValueError


def _check_href(href: object) -> None:
    if (
        not isinstance(href, str)
        or not href
        or any(char.isspace() or _unsafe_character(char) or char in '\\<>"^\x60{}|'
               for char in href)
        or _BAD_ESCAPE.search(href)
    ):
        raise ExternalLinkContractError("External link URL is invalid.")

    try:
        parsed = urlsplit(href)
    except ValueError:
        raise ExternalLinkContractError("External link URL is invalid.") from None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ExternalLinkContractError("External link must use HTTP or HTTPS and have a destination.")
    if parsed.username is not None or parsed.password is not None:
        raise ExternalLinkContractError("Embedded credentials are forbidden.")
    try:
        _check_authority(parsed.netloc)
        _ = parsed.port  # The accessor checks the numeric range.
    except ValueError:
        raise ExternalLinkContractError("External link destination or port is invalid.") from None

    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & _SESSION_KEYS:
        raise ExternalLinkContractError("Session credential query keys are forbidden.")


def validate_external_links(links: tuple[ExternalLink, ...]) -> None:
    """Check ordering, exact label uniqueness and offline URL rules."""
    if not links:
        raise ExternalLinkContractError("External-link registry is empty.")
    if len(links) > MAX_LINKS:
        raise ExternalLinkContractError("External-link registry exceeds the 1024-entry limit.")

    labels = []
    for link in links:
        if (
            not isinstance(link, ExternalLink)
            or not isinstance(link.label, str)
            or not link.label.strip()
            or any(_unsafe_character(char) for char in link.label)
        ):
            raise ExternalLinkContractError("External-link label is invalid.")
        labels.append(link.label)
    if labels != sorted(labels, key=str.casefold):
        raise ExternalLinkContractError("External-link registry is not sorted A-Z.")
    if len(labels) != len(set(labels)):
        raise ExternalLinkContractError("External-link labels are not unique.")

    for link in links:
        _check_href(link.href)


def _regular_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ExternalLinkContractError("Duplicate JSON field in the registry.")
    return result


def _read_registry(path: Path) -> tuple[ExternalLink, ...]:
    try:
        selected = path.lstat()
        if not _regular_file(selected):
            raise ExternalLinkContractError("Registry input must be an ordinary file.")
        if selected.st_size > MAX_INPUT_BYTES:
            raise ExternalLinkContractError("Registry file exceeds the 256 KiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _regular_file(opened) or not os.path.samestat(selected, opened):
                raise ExternalLinkContractError("Registry input changed while opening.")
            data = stream.read(MAX_INPUT_BYTES + 1)
    except ExternalLinkContractError:
        raise
    except (OSError, ValueError):
        raise ExternalLinkContractError("Unable to read the registry file.") from None
    if len(data) > MAX_INPUT_BYTES:
        raise ExternalLinkContractError("Registry file exceeds the 256 KiB limit.")

    try:
        raw = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
    except ExternalLinkContractError:
        raise
    except (ValueError, RecursionError):
        raise ExternalLinkContractError("Registry file must contain valid UTF-8 JSON.") from None

    if not isinstance(raw, list):
        raise ExternalLinkContractError("Registry JSON must contain an array of links.")
    if len(raw) > MAX_LINKS:
        raise ExternalLinkContractError("External-link registry exceeds the 1024-entry limit.")
    result = []
    for entry in raw:
        if (
            not isinstance(entry, dict)
            or entry.keys() != {"label", "href"}
            or not isinstance(entry["label"], str)
            or not isinstance(entry["href"], str)
        ):
            raise ExternalLinkContractError("Registry entries must have label and href text fields.")
        result.append(ExternalLink(entry["label"], entry["href"]))
    return tuple(result)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ExternalLinkContractError("Invalid arguments. Use --help for usage.")


def main(
    argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = _ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 registry JSON.")
    try:
        args = parser.parse_args(argv)
        links = _read_registry(args.input)
        validate_external_links(links)
    except ExternalLinkContractError as error:
        errors.write(f"ERROR: {error}\n")
        return 2

    json.dump({"status": "valid", "count": len(links)}, output)
    output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
