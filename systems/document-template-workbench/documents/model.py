"""Pure semantic composition; substitutions are literal and never recursive."""
import re
from . import contracts as c,runtime as r

def compose(template,values,selected):
    c.template(template);c.values(template,values);c.selection(template,selected);declared={v['name']:v for v in template['fields']}
    def substitute(text):
        result=re.sub(r'\{\{([A-Za-z][A-Za-z0-9_]{0,31})\}\}',lambda m:str(values[m[1]]),text).replace('\r\n','\n').replace('\r','\n');c.text(result,2400);return result
    title=substitute(template['title']);c.text(title,200);sections=[];paragraphs=0;tables=0;rows=0
    for source in template['sections']:
        if source['id'] not in selected:continue
        blocks=[]
        for block in source['blocks']:
            if block['kind']!='table':blocks.append(dict(kind=block['kind'],text=substitute(block['text'])));paragraphs+=1;continue
            schema={col['name']:col for col in declared[block['source']]['columns']};columns=[dict(name=col['field'],label=schema[col['field']]['label'],kind=schema[col['field']]['kind'],width=col['width']) for col in block['columns']];data=[[(row[col['name']].replace('\r\n','\n').replace('\r','\n') if type(row[col['name']]) is str else row[col['name']]) for col in columns] for row in values[block['source']]];totals=[dict(field=n,label=schema[n]['label'],quantity=sum(row[n] for row in values[block['source']])) for n in block['totals']]
            blocks.append(dict(kind='table',columns=columns,rows=data,totals=totals));tables+=1;rows+=len(data)
        sections.append(dict(id=source['id'],title=source['title'],blocks=blocks))
    if rows>400: c.fail('DOCUMENT_ROW_LIMIT')
    result=dict(format='outlands-document-preview-v1',title=title,sections=sections,included=[s['id'] for s in sections],omitted=[s['id'] for s in template['sections'] if s['id'] not in selected],template_sha256=r.digest(r.encode(template)),values_sha256=r.digest(r.encode(values)),summary=dict(sections=len(sections),paragraphs=paragraphs,tables=tables,table_rows=rows))
    if len(r.encode(result))>c.MAX_PREVIEW:c.fail('PREVIEW_LIMIT')
    return result
