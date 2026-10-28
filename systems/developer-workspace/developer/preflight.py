"""Retained owner-authored conservative SQL preflight; engine authorization is separate."""
import re


def _masked_sql(sql: str) -> str:
    """Hide comments and string literals before a conservative query check."""
    chars = list(sql)
    i = 0
    while i < len(sql):
        if sql.startswith('--', i):
            while i < len(sql) and sql[i] not in '\r\n':
                chars[i] = ' '
                i += 1
        elif sql.startswith('/*', i):
            depth = 1
            chars[i] = chars[i + 1] = ' '
            i += 2
            while i < len(sql) and depth:
                if sql.startswith('/*', i):
                    depth += 1
                    chars[i] = chars[i + 1] = ' '
                    i += 2
                elif sql.startswith('*/', i):
                    depth -= 1
                    chars[i] = chars[i + 1] = ' '
                    i += 2
                else:
                    if sql[i] not in '\r\n':
                        chars[i] = ' '
                    i += 1
        elif sql[i] == "'":
            chars[i] = ' '
            i += 1
            while i < len(sql):
                chars[i] = ' '
                if sql[i] == "'":
                    i += 1
                    if i < len(sql) and sql[i] == "'":
                        chars[i] = ' '
                        i += 1
                        continue
                    break
                i += 1
        else:
            i += 1
    return ''.join(chars)


def _check_query(sql: str) -> None:
    code = _masked_sql(sql).strip()
    if not re.match(r'(?is)^(SELECT|WITH)\b', code):
        raise ValueError('This workbench runs one SELECT or CTE query at a time.')
    if code.rstrip(';').find(';') != -1:
        raise ValueError('Run one query at a time; multiple statements are disabled.')
    if re.search(r'(?i)\b(?:INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|EXEC(?:UTE)?|GRANT|REVOKE|DENY|INTO|DBCC|BACKUP|RESTORE|USE)\b', code):
        raise ValueError('This profile blocks statements that may change data or run procedures.')
