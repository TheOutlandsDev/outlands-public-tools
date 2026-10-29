"""Render an explicit literal template. No expressions, includes or HTML input."""
import html
import re
import toolkit as t
from message_core import text


def render(template_raw, variables_raw):
    spec, values = t.decode(template_raw), t.decode(variables_raw)
    t.fields(spec, {'format', 'template', 'variables'})
    t.require(spec['format'] == 'outlands-message-template-v1', 'TEMPLATE_FORMAT_INVALID')
    template = text(spec['template'], multiline=True)
    t.require(bool(template.strip()), 'TEMPLATE_EMPTY')
    names = spec['variables']
    t.require(type(names) is list and len(names) <= 32 and all(type(x) is str for x in names), 'VARIABLE_LIMIT')
    for name in names:
        t.identifier(name)
    t.require(len(set(names)) == len(names), 'DUPLICATE_VARIABLE')
    tokens = re.findall(r'\{\{([a-z][a-z0-9_-]{0,47})\}\}', template)
    residual = re.sub(r'\{\{([a-z][a-z0-9_-]{0,47})\}\}', '', template)
    t.require('{' not in residual and '}' not in residual and len(tokens) <= 128, 'PLACEHOLDER_INVALID')
    t.require(set(tokens) == set(names), 'VARIABLE_DECLARATION_MISMATCH')
    t.fields(values, {'format', 'values'})
    t.require(values['format'] == 'outlands-message-values-v1', 'VALUES_FORMAT_INVALID')
    t.fields(values['values'], names)
    for value in values['values'].values():
        text(value, 2048, multiline=True)
    rendered = re.sub(r'\{\{([a-z][a-z0-9_-]{0,47})\}\}', lambda m: values['values'][m[1]], template)
    t.require(len(rendered.encode('utf-8')) <= 65536, 'RENDER_LIMIT')
    return {'status':'PASS', 'format':'outlands-rendered-message-v1',
            'template_sha256':t.digest(template_raw), 'values_sha256':t.digest(variables_raw),
            'text':rendered, 'html':'<pre>' + html.escape(rendered, quote=True) + '</pre>',
            'html_policy':'ALL_LITERAL_CONTENT_ESCAPED', 'network_used':False}


def main(argv=None):
    p = t.Parser(description='Render selected literal templates; output contains supplied values.')
    p.add_argument('--template', required=True)
    p.add_argument('--values', required=True)
    p.add_argument('--out')
    return t.run(p, lambda a: render(t.read(a.template), t.read(a.values)), argv)


if __name__ == '__main__':
    raise SystemExit(main())
