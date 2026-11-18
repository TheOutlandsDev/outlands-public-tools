"""Advisory text classification for RDL SQL Server CommandText.

This module never executes SQL. Its flags are clues for human review, not a
SQL parser, a permission check, or evidence that a query is safe to run.
"""

from __future__ import annotations

import re


_IDENTIFIER = r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][A-Za-z0-9_@$#]*)'

# An explicit three-part object name after a table-reference keyword is a
# probable database dependency. Known MES databases are also detected when a
# qualifier appears elsewhere in the command text.
_TABLE_REFERENCE = re.compile(
    rf"\b(?:FROM|JOIN|INTO|UPDATE|MERGE)\s+(?P<database>{_IDENTIFIER})"
    rf"\s*\.\s*{_IDENTIFIER}\s*\.\s*{_IDENTIFIER}",
    re.IGNORECASE,
)
_MES_REFERENCE = re.compile(
    rf"(?<![A-Za-z0-9_])(?P<database>\[?DEMO_MES(?:ODS|DWH)?\]?)"
    rf"\s*\.\s*(?:{_IDENTIFIER})?\s*\.\s*{_IDENTIFIER}",
    re.IGNORECASE,
)

_FEATURE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("declare_variable", re.compile(r"\bDECLARE\s+@[A-Za-z_]\w*", re.IGNORECASE)),
    ("top", re.compile(r"\bTOP\s*(?:\(|\d|@)", re.IGNORECASE)),
    ("isnull", re.compile(r"\bISNULL\s*\(", re.IGNORECASE)),
    ("getdate", re.compile(r"\bGETDATE\s*\(", re.IGNORECASE)),
    ("dateadd", re.compile(r"\bDATEADD\s*\(", re.IGNORECASE)),
    ("datediff", re.compile(r"\bDATEDIFF\s*\(", re.IGNORECASE)),
    ("convert", re.compile(r"\bCONVERT\s*\(", re.IGNORECASE)),
    ("apply", re.compile(r"\b(?:CROSS|OUTER)\s+APPLY\b", re.IGNORECASE)),
    ("temp_table", re.compile(r"(?<![A-Za-z0-9_#])#{1,2}[A-Za-z_]\w*")),
    ("table_variable", re.compile(r"\bDECLARE\s+@[A-Za-z_]\w*\s+(?:AS\s+)?TABLE\b", re.IGNORECASE)),
    ("at_time_zone", re.compile(r"\bAT\s+TIME\s+ZONE\b", re.IGNORECASE)),
    ("pivot", re.compile(r"\bPIVOT\b", re.IGNORECASE)),
    ("exec", re.compile(r"\bEXEC(?:UTE)?\b", re.IGNORECASE)),
    ("table_hint", re.compile(r"\b(?:NOLOCK|FORCESEEK)\b", re.IGNORECASE)),
    ("query_governor", re.compile(r"\bQUERY_GOVERNOR_COST_LIMIT\b", re.IGNORECASE)),
)

_POSSIBLE_DATA_WRITE = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|MERGE|TRUNCATE)\b|\bINTO\s+(?:#|@|\[|[A-Za-z_])",
    re.IGNORECASE,
)
_POSSIBLE_DDL = re.compile(r"\b(?:CREATE|ALTER|DROP)\b", re.IGNORECASE)
_HAS_SELECT = re.compile(r"\bSELECT\b", re.IGNORECASE)


def _mask_comments_and_literals(sql: str) -> str:
    """Replace comments and single-quoted literals with spaces.

    Line breaks remain in place. Nested block comments and doubled SQL quote
    escapes are handled so text inside them cannot look like executable SQL.
    """

    chars = list(sql)
    index = 0
    length = len(chars)
    while index < length:
        if sql.startswith("--", index):
            while index < length and sql[index] not in "\r\n":
                chars[index] = " "
                index += 1
            continue

        if sql.startswith("/*", index):
            depth = 1
            chars[index] = chars[index + 1] = " "
            index += 2
            while index < length and depth:
                if sql.startswith("/*", index):
                    depth += 1
                    chars[index] = chars[index + 1] = " "
                    index += 2
                elif sql.startswith("*/", index):
                    depth -= 1
                    chars[index] = chars[index + 1] = " "
                    index += 2
                else:
                    if chars[index] not in "\r\n":
                        chars[index] = " "
                    index += 1
            continue

        if sql[index] == "'":
            chars[index] = " "
            index += 1
            while index < length:
                if sql[index] == "'":
                    chars[index] = " "
                    index += 1
                    if index < length and sql[index] == "'":
                        chars[index] = " "
                        index += 1
                        continue
                    break
                if chars[index] not in "\r\n":
                    chars[index] = " "
                index += 1
            continue

        index += 1

    return "".join(chars)


def _database_name(identifier: str) -> str:
    if identifier.startswith("[") and identifier.endswith("]"):
        identifier = identifier[1:-1].replace("]]", "]")
    elif identifier.startswith('"') and identifier.endswith('"'):
        identifier = identifier[1:-1].replace('""', '"')
    return identifier.upper()


def classify_sql(sql: str) -> dict[str, list[str]]:
    """Return deterministic advisory lists for raw RDL CommandText.

    The output keys are ``tsql_features``, ``external_database_refs``, and
    ``review_flags``. Database references are names from probable three-part
    objects, not proof that those objects exist or are accessible. Any write
    flag means only that review is needed; the scan is intentionally cautious.
    """

    if not isinstance(sql, str):
        raise TypeError("sql must be a string")

    code = _mask_comments_and_literals(sql)
    features = sorted(name for name, pattern in _FEATURE_PATTERNS if pattern.search(code))
    databases = {
        _database_name(match.group("database"))
        for pattern in (_TABLE_REFERENCE, _MES_REFERENCE)
        for match in pattern.finditer(code)
    }

    flags: set[str] = set()
    if databases:
        flags.add("external_database_reference")
    if "exec" in features:
        flags.add("procedure_or_dynamic_sql_review")
    if _POSSIBLE_DATA_WRITE.search(code):
        flags.add("possible_write")
    if _POSSIBLE_DDL.search(code):
        flags.add("possible_ddl")
    if sql.lstrip().startswith("="):
        flags.add("rdl_expression_review")
    if not _HAS_SELECT.search(code) and "exec" not in features:
        flags.add("no_select_detected")

    return {
        "tsql_features": features,
        "external_database_refs": sorted(databases),
        "review_flags": sorted(flags),
    }
