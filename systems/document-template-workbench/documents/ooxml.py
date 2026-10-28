"""Fresh constrained OOXML only: no incoming DOCX, media, macros or external links."""
import io
import stat
import zipfile
from xml.etree import ElementTree as E
from . import contracts as c,runtime as r

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
OFFICE='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
CP='http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
DC='http://purl.org/dc/elements/1.1/'
DCT='http://purl.org/dc/terms/'
XSI='http://www.w3.org/2001/XMLSchema-instance'
APP='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
E.register_namespace('w',W);E.register_namespace('cp',CP);E.register_namespace('dc',DC);E.register_namespace('dcterms',DCT);E.register_namespace('xsi',XSI)

def tag(name):return '{'+W+'}'+name
def node(parent,name,**attrs):return E.SubElement(parent,tag(name),{tag(k):str(v) for k,v in attrs.items()})
def xml(root):return E.tostring(root,encoding='utf-8',xml_declaration=True)
def paragraph(parent,text,style=None,align=None,bold=False,color=None):
    p=node(parent,'p');pr=node(p,'pPr')
    if style:node(pr,'pStyle',val=style)
    if align:node(pr,'jc',val=align)
    if style=='Bullet':node(pr,'ind',left=360,hanging=240);text='\u2022 '+text
    run=node(p,'r')
    if bold or color:
        rp=node(run,'rPr')
        if bold:node(rp,'b')
        if color:node(rp,'color',val=color)
    chunks=text.replace('\r\n','\n').replace('\r','\n').split('\n')
    for index,chunk in enumerate(chunks):
        if index:node(run,'br')
        for number,part in enumerate(chunk.split('\t')):
            if number:node(run,'tab')
            t=node(run,'t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=part
    return p
def styles():
    root=E.Element(tag('styles'));defaults=node(root,'docDefaults');rp=node(node(defaults,'rPrDefault'),'rPr');node(rp,'rFonts',ascii='Arial',hAnsi='Arial',eastAsia='Arial',cs='Arial');node(rp,'sz',val=22);node(rp,'color',val='000000');pp=node(node(defaults,'pPrDefault'),'pPr');node(pp,'spacing',after=120,line=276,lineRule='auto')
    for identifier,label,size,bold,before,after in [('Normal','Normal',22,False,0,120),('Title','Title',44,False,0,240),('Heading1','Heading 1',30,True,240,120),('Bullet','Bullet',22,False,0,100)]:
        style=node(root,'style',type='paragraph',styleId=identifier)
        if identifier=='Normal':style.set(tag('default'),'1')
        node(style,'name',val=label)
        if identifier!='Normal':node(style,'basedOn',val='Normal')
        pp=node(style,'pPr')
        if identifier in ('Title','Heading1'):node(pp,'keepNext');node(pp,'keepLines')
        node(pp,'spacing',before=before,after=after,line=276,lineRule='auto')
        if identifier=='Heading1':node(pp,'outlineLvl',val=0)
        rp=node(style,'rPr');node(rp,'sz',val=size);node(rp,'color',val='000000')
        if bold:node(rp,'b')
    return root
def table(body,block):
    columns=block['columns'];tbl=node(body,'tbl');pr=node(tbl,'tblPr');node(pr,'tblW',w=9360,type='dxa');node(pr,'tblLayout',type='fixed');borders=node(pr,'tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):node(borders,edge,val='single',sz=4,color='D9D9D9')
    margins=node(pr,'tblCellMar')
    for edge,value in [('top',90),('left',110),('bottom',90),('right',110)]:node(margins,edge,w=value,type='dxa')
    widths=[9360*col['width']//100 for col in columns];widths[-1]=9360-sum(widths[:-1]);grid=node(tbl,'tblGrid')
    for width in widths:node(grid,'gridCol',w=width)
    for index,values in enumerate([[col['label'] for col in columns],*block['rows']]):
        tr=node(tbl,'tr');tp=node(tr,'trPr');node(tp,'cantSplit')
        if index==0:node(tp,'tblHeader')
        for col,width,value in zip(columns,widths,values):
            cell=node(tr,'tc');cp=node(cell,'tcPr');node(cp,'tcW',w=width,type='dxa');node(cp,'vAlign',val='center');node(cp,'shd',fill='203746' if index==0 else ('F2F5F7' if index%2==0 else 'FFFFFF'))
            p=paragraph(cell,str(value),align='right' if col['kind']=='quantity' else 'left',bold=index==0,color='FFFFFF' if index==0 else '000000');spacing=E.Element(tag('spacing'),{tag(k):str(v) for k,v in dict(before=40,after=40,line=264,lineRule='auto').items()});p.find(tag('pPr')).insert(0,spacing)
    for total in block['totals']:paragraph(body,'Total '+total['label'].lower()+' '+str(total['quantity']),bold=True)
    paragraph(body,'')
def parts(model):
    document=E.Element(tag('document'));body=node(document,'body');paragraph(body,model['title'],style='Title')
    for section in model['sections']:
        paragraph(body,section['title'],style='Heading1')
        for block in section['blocks']:
            if block['kind']=='table':table(body,block)
            else:paragraph(body,block['text'],style='Bullet' if block['kind']=='bullet' else 'Normal')
    section=node(body,'sectPr');node(section,'pgSz',w=12240,h=15840);node(section,'pgMar',top=1440,right=1440,bottom=1440,left=1440,header=720,footer=720,gutter=0)
    settings=E.Element(tag('settings'));node(settings,'defaultTabStop',val=720);node(settings,'characterSpacingControl',val='doNotCompress')
    rels=E.Element('{'+REL+'}Relationships')
    for ident,kind,target in [('rId1',OFFICE+'officeDocument','word/document.xml'),('rId2','http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties','docProps/core.xml'),('rId3',OFFICE+'extended-properties','docProps/app.xml')]:E.SubElement(rels,'{'+REL+'}Relationship',dict(Id=ident,Type=kind,Target=target))
    docrels=E.Element('{'+REL+'}Relationships')
    for ident,kind,target in [('rId1','styles','styles.xml'),('rId2','settings','settings.xml')]:E.SubElement(docrels,'{'+REL+'}Relationship',dict(Id=ident,Type=OFFICE+kind,Target=target))
    core=E.Element('{'+CP+'}coreProperties')
    for name,text in [('{'+DC+'}title','Generated document'),('{'+DC+'}creator','OUTLANDS'),('{'+CP+'}lastModifiedBy','OUTLANDS'),('{'+DC+'}description','Private generated document')]:E.SubElement(core,name).text=text
    for name in ('created','modified'):item=E.SubElement(core,'{'+DCT+'}'+name,{'{'+XSI+'}type':'dcterms:W3CDTF'});item.text='2020-01-01T00:00:00Z'
    props=E.Element('{'+APP+'}Properties');E.SubElement(props,'{'+APP+'}Application').text='OUTLANDS';E.SubElement(props,'{'+APP+'}AppVersion').text='1.0'
    content=E.Element('{'+CT+'}Types')
    for ext,mime in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('xml','application/xml')]:E.SubElement(content,'{'+CT+'}Default',dict(Extension=ext,ContentType=mime))
    for name,mime in [('word/document.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'),('word/styles.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml'),('word/settings.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml'),('docProps/core.xml','application/vnd.openxmlformats-package.core-properties+xml'),('docProps/app.xml','application/vnd.openxmlformats-officedocument.extended-properties+xml')]:E.SubElement(content,'{'+CT+'}Override',dict(PartName='/'+name,ContentType=mime))
    result={'[Content_Types].xml':xml(content),'_rels/.rels':xml(rels),'docProps/core.xml':xml(core),'docProps/app.xml':xml(props),'word/document.xml':xml(document),'word/styles.xml':xml(styles()),'word/settings.xml':xml(settings),'word/_rels/document.xml.rels':xml(docrels)}
    if sum(map(len,result.values()))>c.MAX_DOCX:c.fail('DOCX_SIZE_LIMIT')
    return result
def build(model):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as z:
        for name,raw in sorted(parts(model).items()):
            info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_STORED;z.writestr(info,raw)
    raw=output.getvalue()
    if len(raw)>c.MAX_DOCX:c.fail('DOCX_SIZE_LIMIT')
    return raw
def inspect(raw,model):
    if len(raw)>c.MAX_DOCX:c.fail('DOCX_SIZE_LIMIT')
    expected=parts(model)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if len(z.infolist())!=8 or set(z.namelist())!=set(expected):c.fail('DOCX_PARTS_REFUSED')
            if any(item.file_size>c.MAX_DOCX or item.compress_type!=zipfile.ZIP_STORED or item.flag_bits&1 for item in z.infolist()):c.fail('DOCX_MEMBER_REFUSED')
            if z.comment or any(item.extra or item.comment or item.date_time!=(2020,1,1,0,0,0) or item.create_system!=3 or item.external_attr>>16!=(stat.S_IFREG|0o644) for item in z.infolist()):c.fail('DOCX_METADATA_REFUSED')
            for name,content in expected.items():
                member=z.read(name)
                if member!=content or b'<!DOCTYPE' in member or b'<!ENTITY' in member:c.fail('DOCX_CONTENT_MISMATCH')
                E.fromstring(member)
            doc=E.fromstring(z.read('word/document.xml'));headers=doc.findall('.//'+tag('tblHeader'));core=E.fromstring(z.read('docProps/core.xml'))
            if len(headers)!=model['summary']['tables'] or core.find('{'+DC+'}creator').text!='OUTLANDS':c.fail('DOCX_CONTRACT_MISMATCH')
    except (zipfile.BadZipFile,KeyError,E.ParseError,RuntimeError):c.fail('DOCX_PACKAGE_INVALID')
    return dict(parts=8,external_relationships=0,media_parts=0,macros=0,template_thumbnail_parts=0,neutral_core_properties=True,repeat_table_headers=len(headers),letter_portrait=True,model_matched=True)
