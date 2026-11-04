"""Bounded, unmapped CSV column counts without exposing cell values."""
import csv
import io
import toolkit as t


def profile(text):
    t.require(type(text) is str and len(text.encode('utf-8')) <= 4096, 'CSV_LIMIT')
    try:
        records = list(csv.reader(io.StringIO(text, newline=''), dialect='excel', strict=True))
    except (csv.Error, UnicodeError):
        raise t.Rejected('CSV_INVALID') from None
    t.require(2 <= len(records) <= 513, 'CSV_ROW_LIMIT')
    headers = records[0]
    t.require(1 <= len(headers) <= 32, 'CSV_COLUMN_LIMIT')
    for header in headers:
        t.identifier(header)
    t.require(len(set(headers)) == len(headers), 'CSV_HEADER_DUPLICATE')
    for row in records[1:]:
        t.require(len(row) == len(headers), 'CSV_ROW_WIDTH_INVALID')
        t.require(all(len(cell) <= 256 for cell in row), 'CSV_CELL_LIMIT')
    columns = []
    for index, header in enumerate(headers):
        values = [row[index] for row in records[1:]]
        nonblank = [cell for cell in values if cell != '']
        columns.append({'header': header, 'blank_rows': len(values) - len(nonblank),
                        'nonblank_rows': len(nonblank), 'distinct_nonblank': len(set(nonblank)),
                        'minimum_length': min(map(len, nonblank)) if nonblank else None,
                        'maximum_length': max(map(len, nonblank)) if nonblank else None})
    result = {'row_count': len(records) - 1, 'headers': headers, 'columns': columns}
    return result, t.digest(t.encode(result)), t.digest(text.encode('utf-8'))
