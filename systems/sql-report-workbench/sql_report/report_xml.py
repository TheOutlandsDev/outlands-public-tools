"""Bounded offline Report/RDL subset; no external bindings, expressions or rendering."""
import re
import xml.etree.ElementTree as ET
from . import contracts as c,runtime as r

NAMESPACES={'urn:outlands:offline-report:v1',*{'http://schemas.microsoft.com/sqlserver/reporting/'+year+'/reportdefinition' for year in ('2008/01','2010/01','2016/01')}}
FORBIDDEN={'ConnectionProperties','ConnectString','DataSourceReference','SharedDataSetReference','DataSourceName','Code','CodeModules','EmbeddedImages','Image','Subreport','Hyperlink','DefaultValue'}


def inspect(raw):
    if len(raw)>512*1024:raise r.WorkbenchError('REPORT_SIZE_LIMIT')
    try:text=raw.decode('utf-8-sig')
    except UnicodeError:raise r.WorkbenchError('REPORT_UTF8_REQUIRED') from None
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',text,re.I):raise r.WorkbenchError('XML_DECLARATION_REFUSED')
    try:root=ET.fromstring(text)
    except (ET.ParseError,ValueError):raise r.WorkbenchError('XML_INVALID') from None
    if not isinstance(root.tag,str) or not root.tag.startswith('{') or root.tag.split('}',1)[1]!='Report':raise r.WorkbenchError('REPORT_ROOT_INVALID')
    namespace=root.tag[1:].split('}',1)[0]
    if namespace not in NAMESPACES:raise r.WorkbenchError('REPORT_NAMESPACE_UNSUPPORTED')
    prefix='{'+namespace+'}';stack=[(root,0)];count=0
    while stack:
        node,depth=stack.pop();count+=1
        if count>5000 or depth>40 or len(node.attrib)>16 or len(node.text or '')>16384:raise r.WorkbenchError('XML_STRUCTURE_LIMIT')
        if not node.tag.startswith(prefix):raise r.WorkbenchError('XML_NAMESPACE_MIXED')
        if node.tag[len(prefix):] in FORBIDDEN:raise r.WorkbenchError('REPORT_EXTERNAL_OR_EXECUTABLE_CONTENT')
        stack.extend((child,depth+1) for child in node)
    def one(parent,name,required=True):
        values=parent.findall(prefix+name)
        if len(values)>1 or required and len(values)!=1:raise r.WorkbenchError('REPORT_CARDINALITY_INVALID')
        return values[0] if values else None
    def children(parent,name):return parent.findall(prefix+name) if parent is not None else []
    def value(parent,name):return one(parent,name).text or ''
    parameters={};param_root=one(root,'ReportParameters',False)
    for parameter in children(param_root,'ReportParameter'):
        name=c.identifier(parameter.get('Name'));kind={'Integer':'integer','Float':'real','String':'text'}.get(value(parameter,'DataType').strip())
        if name in parameters or kind is None:raise r.WorkbenchError('REPORT_PARAMETER_INVALID')
        parameters[name]=kind
    if len(parameters)>32:raise r.WorkbenchError('PARAMETER_LIMIT')
    datasets=[];seen=set();data_root=one(root,'DataSets')
    for node in children(data_root,'DataSet'):
        name=c.identifier(node.get('Name'))
        if name in seen:raise r.WorkbenchError('REPORT_DATASET_DUPLICATE')
        seen.add(name);query=one(node,'Query');command_type=one(query,'CommandType',False)
        if command_type is not None and (command_type.text or '').strip()!='Text':raise r.WorkbenchError('REPORT_COMMAND_TYPE_REFUSED')
        sql=value(query,'CommandText');links={};query_params=one(query,'QueryParameters',False)
        for parameter in children(query_params,'QueryParameter'):
            key=c.identifier((parameter.get('Name') or '').removeprefix(':'));expression=value(parameter,'Value').strip();match=re.fullmatch(r'=Parameters!([a-z][a-z0-9_]*)\.Value',expression)
            if not match or match[1] not in parameters or key in links:raise r.WorkbenchError('REPORT_PARAMETER_EXPRESSION_REFUSED')
            links[key]=match[1]
        definition=c.query(r.encode(dict(format='outlands-sql-query-v1',query_id='report-query',title='Offline report query',sql=sql,parameters={key:parameters[target] for key,target in links.items()})))
        fields=[];field_root=one(node,'Fields')
        for field in children(field_root,'Field'):
            field_name=c.identifier(field.get('Name'));column=c.identifier(value(field,'DataField').strip())
            if field_name in {item['name'] for item in fields}:raise r.WorkbenchError('REPORT_FIELD_DUPLICATE')
            fields.append(dict(name=field_name,column=column))
        if not 1<=len(fields)<=32:raise r.WorkbenchError('REPORT_FIELD_LIMIT')
        datasets.append(dict(name=name,sql=definition['sql'],parameters=definition['parameters'],parameter_links=links,fields=fields))
    if not 1<=len(datasets)<=8:raise r.WorkbenchError('REPORT_DATASET_LIMIT')
    return dict(format='outlands-offline-report-v1',namespace=namespace,parameters=parameters,datasets=datasets,source_sha256=r.digest(raw),rendered=False,external_connections_used=False,scope='Structural offline subset; not full RDL schema or report-server validation')


def checked_text(relative,expected_sha256):
    # Adapt the authored catalog path + hash + UTF-8 boundary to native guarded I/O.
    c.hash_value(expected_sha256);raw=r.read_bytes(r.local_path(relative),512*1024)
    if r.digest(raw)!=expected_sha256:raise r.WorkbenchError('REPORT_SOURCE_HASH_MISMATCH')
    return raw
