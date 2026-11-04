"""A deliberately narrow, bounded HTML table grid parser."""
from html.parser import HTMLParser
import toolkit as t

MAX_HTML = 4096
MAX_TABLES = 16
MAX_ROWS = 128
MAX_COLUMNS = 32
MAX_CELLS = 1024


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.tables = []
        self.rows = None
        self.row = None
        self.cell = None
        self.text = []
        self.cell_count = 0

    def handle_starttag(self, tag, attrs):
        t.require(tag in {'table', 'tr', 'td', 'th'}, 'HTML_TAG_UNSUPPORTED')
        parent = self.stack[-1] if self.stack else None
        t.require((tag, parent) in {('table', None), ('tr', 'table'),
                                    ('td', 'tr'), ('th', 'tr')}, 'HTML_NESTING_INVALID')
        if tag in {'table', 'tr'}:
            t.require(not attrs, 'HTML_ATTRIBUTE_UNSUPPORTED')
        else:
            values = {}
            for key, value in attrs:
                t.require(key in {'rowspan', 'colspan'} and key not in values,
                          'HTML_ATTRIBUTE_UNSUPPORTED')
                t.require(type(value) is str and value.isascii() and value.isdecimal()
                          and value[0] != '0', 'HTML_SPAN_INVALID')
                number = int(value)
                t.require(1 <= number <= 16, 'HTML_SPAN_INVALID')
                values[key] = number
            self.cell = {'text': '', 'header': tag == 'th',
                         'rowspan': values.get('rowspan', 1),
                         'colspan': values.get('colspan', 1)}
            self.text = []
            self.cell_count += 1
            t.require(self.cell_count <= MAX_CELLS, 'HTML_CELL_LIMIT')
        if tag == 'table':
            t.require(len(self.tables) < MAX_TABLES, 'HTML_TABLE_LIMIT')
            self.rows = []
        elif tag == 'tr':
            self.row = []
        self.stack.append(tag)

    def handle_endtag(self, tag):
        t.require(self.stack and self.stack[-1] == tag, 'HTML_NESTING_INVALID')
        self.stack.pop()
        if tag in {'td', 'th'}:
            self.cell['text'] = ''.join(self.text)
            t.require(len(self.cell['text']) <= 256, 'HTML_CELL_TEXT_LIMIT')
            self.row.append(self.cell)
            self.cell = None
            self.text = []
        elif tag == 'tr':
            t.require(self.row and len(self.rows) < MAX_ROWS, 'HTML_ROW_LIMIT')
            self.rows.append(self.row)
            self.row = None
        elif tag == 'table':
            t.require(self.rows, 'HTML_ROW_LIMIT')
            self.tables.append(self.rows)
            self.rows = None

    def handle_data(self, data):
        if self.cell is None:
            t.require(not data.strip(), 'HTML_TEXT_OUTSIDE_CELL')
        else:
            self.text.append(data)
            t.require(sum(map(len, self.text)) <= 256, 'HTML_CELL_TEXT_LIMIT')

    def handle_startendtag(self, tag, attrs):
        raise t.Rejected('HTML_TAG_UNSUPPORTED')

    def handle_comment(self, data):
        raise t.Rejected('HTML_COMMENT_UNSUPPORTED')

    def handle_decl(self, decl):
        raise t.Rejected('HTML_DECLARATION_UNSUPPORTED')

    def handle_pi(self, data):
        raise t.Rejected('HTML_DECLARATION_UNSUPPORTED')

    def unknown_decl(self, data):
        raise t.Rejected('HTML_DECLARATION_UNSUPPORTED')


def grid(html, table):
    t.require(type(html) is str and len(html.encode('utf-8')) <= MAX_HTML, 'HTML_LIMIT')
    t.integer(table, MAX_TABLES, 1)
    parser = Tables()
    try:
        parser.feed(html)
        parser.close()
    except t.Rejected:
        raise
    except (ValueError, UnicodeError, OverflowError):
        raise t.Rejected('HTML_INVALID') from None
    t.require(not parser.stack and parser.tables, 'HTML_NESTING_INVALID')
    t.require(table <= len(parser.tables), 'HTML_TABLE_UNKNOWN')
    rows = parser.tables[table - 1]
    occupied = {}
    for r, source_row in enumerate(rows):
        c = 0
        for cell in source_row:
            while (r, c) in occupied:
                c += 1
            t.require(c + cell['colspan'] <= MAX_COLUMNS and
                      r + cell['rowspan'] <= len(rows), 'HTML_SPAN_OUT_OF_RANGE')
            for rr in range(r, r + cell['rowspan']):
                for cc in range(c, c + cell['colspan']):
                    t.require((rr, cc) not in occupied, 'HTML_SPAN_OVERLAP')
                    occupied[rr, cc] = {'text': cell['text'], 'header': cell['header'],
                                        'anchor': [r + 1, c + 1]}
            c += cell['colspan']
    width = max(c for _, c in occupied) + 1
    t.require(width <= MAX_COLUMNS and len(occupied) == len(rows) * width,
              'HTML_GRID_NOT_RECTANGULAR')
    matrix = [[occupied[r, c] for c in range(width)] for r in range(len(rows))]
    result = {'table': table, 'rows': len(matrix), 'columns': width, 'cells': matrix}
    return result, t.digest(t.encode(result)), len(parser.tables)
