"""Explicit visual snapshots, bounded integer geometry and conservative scope checks."""
from fractions import Fraction
import re
import toolkit as t
import decision_core as c

LINK={'id','revision','image','image_revision','image_snapshot_sha256'}

def image(row):
    key,out=c.record(row,{'id','revision','content_sha256','width','height'},('id',),('revision',))
    t.sha(row['content_sha256'])
    for axis in ('width','height'):t.integer(row[axis],10**6,1)
    return key,out

def coordinate(value):return t.integer(value,2*10**6,-10**6)

def vertices(value):
    t.require(type(value) is list and 3<=len(value)<=128,'VERTEX_LIMIT')
    for point in value:
        t.require(type(point) is list and len(point)==2,'POINT_INVALID')
        for v in point:coordinate(v)
    return [list(p) for p in value]

def pixel_box(value):
    t.fields(value,{'left','top','right','bottom'})
    for n in value.values():coordinate(n)
    return dict(value)

def linked(row,extra):
    key,out=c.record(row,LINK|extra,('id','image'),('revision','image_revision'))
    t.sha(row['image_snapshot_sha256']);return key,out

def annotation(row):
    key,out=linked(row,{'label','taxonomy_sha256','kind','geometry'})
    t.identifier(row['label']);t.sha(row['taxonomy_sha256'])
    t.require(row['kind'] in ('polygon','box'),'GEOMETRY_KIND_INVALID')
    out['geometry']=vertices(row['geometry']) if row['kind']=='polygon' else pixel_box(row['geometry'])
    return key,out

def polygon(row):
    key,out=linked(row,{'vertices'});out['vertices']=vertices(row['vertices']);return key,out

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def reference(row,images,side,position,issues):
    target=images.get(row['image'])
    if target is None:c.issue(issues,side,position,'IMAGE_UNKNOWN');return
    if row['image_revision']!=target[1]['revision'] or row['image_snapshot_sha256']!=c.pin(target[1]):
        c.issue(issues,side,position,'IMAGE_SNAPSHOT_MISMATCH')

def vertex_budget(selected,key):
    count=sum(len(row[key]) for _,row in selected.values())
    t.require(count<=4096,'TOTAL_VERTEX_LIMIT')

def scope(value,counts,issues):
    taxonomy=c.taxonomy(value['taxonomy']);images=collect(value['images'],image,'images',counts,issues)
    annotations=collect(value['annotations'],annotation,'annotations',counts,issues)
    vertex_budget({k:v for k,v in annotations.items() if v[1]['kind']=='polygon'},'geometry')
    tax_pin=c.pin(taxonomy)
    for position,row in annotations.values():
        reference(row,images,'annotations',position,issues)
        if row['taxonomy_sha256']!=tax_pin:c.issue(issues,'annotations',position,'TAXONOMY_PIN_MISMATCH')
        if row['label'] not in taxonomy['labels']:c.issue(issues,'annotations',position,'LABEL_UNKNOWN')
    return taxonomy,images,annotations

def output(raw,fmt,counts,issues,**values):
    report=c.base(raw,fmt,counts,issues)
    report.update(artifact_bytes_verified=False,label_truth_verified=False,
                  content_geometry_alignment_verified=False,approval_authenticity_verified=False,
                  dataset_export_performed=False,**values)
    return report

def cross(a,b,p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])

def on_segment(a,b,p):return cross(a,b,p)==0 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])

def intersects(a,b,p,q):
    abp,abq,pqa,pqb=cross(a,b,p),cross(a,b,q),cross(p,q,a),cross(p,q,b)
    return ((abp>0 and abq<0 or abp<0 and abq>0) and (pqa>0 and pqb<0 or pqa<0 and pqb>0)) or any((on_segment(a,b,p),on_segment(a,b,q),on_segment(p,q,a),on_segment(p,q,b)))

def fraction(numerator,denominator):
    exact=Fraction(numerator,denominator)
    return dict(numerator=numerator,denominator=denominator,exact_fraction=str(exact.numerator)+'/'+str(exact.denominator))

def analyze_polygon(points,width,height):
    count=len(points);failures=[];contacts=[];contact_count=0
    if any(not (0<=x<=width and 0<=y<=height) for x,y in points):failures.append('VERTEX_OUTSIDE_FRAME')
    if len({tuple(p) for p in points})!=count:failures.append('VERTEX_REPEATED')
    if any(points[i]==points[(i+1)%count] for i in range(count)):failures.append('EDGE_ZERO_LENGTH')
    twice=sum(points[i][0]*points[(i+1)%count][1]-points[(i+1)%count][0]*points[i][1] for i in range(count))
    if twice==0:failures.append('AREA_ZERO')
    for i in range(count):
        a,b=points[i],points[(i+1)%count]
        for j in range(i+1,count):
            p,q=points[j],points[(j+1)%count]
            adjacent=j==i+1 or (i==0 and j==count-1)
            if adjacent:
                shared=points[j] if j==i+1 else points[0]
                u=a if a!=shared else b;v=p if p!=shared else q
                contact=cross(shared,u,v)==0 and (u[0]-shared[0])*(v[0]-shared[0])+(u[1]-shared[1])*(v[1]-shared[1])>0
            else:contact=intersects(a,b,p,q)
            if contact:
                contact_count+=1
                if len(contacts)<16:contacts.append(dict(first_edge=i,second_edge=j,kind='adjacent_overlap' if adjacent else 'nonadjacent_contact'))
    if contact_count:failures.append('EDGE_CONTACT')
    return dict(valid=not failures,failed_criteria=sorted(failures),vertex_count=count,twice_signed_area=twice,
        area=fraction(abs(twice),2),orientation='clockwise' if twice>0 else 'counterclockwise' if twice<0 else 'degenerate',
        envelope=dict(left=min(p[0] for p in points),top=min(p[1] for p in points),right=max(p[0] for p in points),bottom=max(p[1] for p in points)),
        edge_contact_count=contact_count,edge_contacts=contacts,edge_contacts_truncated=contact_count>len(contacts))

def unit(value):
    t.require(type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]{0,9})/(?:[1-9][0-9]{0,9})',value),'UNIT_FRACTION_INVALID')
    n,d=map(int,value.split('/'));t.integer(n,10**9);t.integer(d,10**9,1)
    t.require(n<=d,'UNIT_INTERVAL_REQUIRED');return Fraction(n,d)

def fraction_text(value):return str(value.numerator)+'/'+str(value.denominator)

def box(row):
    key,out=linked(row,{'source','target'});source=row['source'];t.fields(source,{'format','values'})
    formats=('pixel-xyxy','pixel-xywh','unit-cxcywh')
    t.require(source['format'] in formats and row['target'] in formats,'BOX_FORMAT_INVALID')
    values=source['values'];t.require(type(values) is list and len(values)==4,'BOX_VALUES_INVALID')
    if source['format']=='unit-cxcywh':values=[fraction_text(unit(v)) for v in values]
    else:
        for v in values:coordinate(v)
    out['source']=dict(format=source['format'],values=list(values));return key,out

def convert_box(row,width,height):
    source=row['source'];values=source['values']
    if source['format']=='unit-cxcywh':
        cx,cy,w,h=map(unit,values);left,right=(cx-w/2)*width,(cx+w/2)*width;top,bottom=(cy-h/2)*height,(cy+h/2)*height
    else:
        a,b,u,v=map(Fraction,values);left,top=a,b
        right,bottom=(u,v) if source['format']=='pixel-xyxy' else (a+u,b+v)
    edges=[left,top,right,bottom];failures=[]
    if right<=left or bottom<=top:failures.append('BOX_AREA_NONPOSITIVE')
    if not (0<=left<=width and 0<=right<=width and 0<=top<=height and 0<=bottom<=height):failures.append('BOX_OUTSIDE_FRAME')
    if any(v.denominator!=1 for v in edges):failures.append('NONINTEGRAL_PIXEL_EDGES')
    converted=None
    if not failures:
        if row['target']=='pixel-xyxy':converted=[int(v) for v in edges]
        elif row['target']=='pixel-xywh':converted=[int(left),int(top),int(right-left),int(bottom-top)]
        else:converted=[fraction_text(v) for v in [(left+right)/(2*width),(top+bottom)/(2*height),(right-left)/width,(bottom-top)/height]]
    return dict(valid=not failures,failed_criteria=failures,pixel_edges=[fraction_text(v) for v in edges],target=row['target'],converted_values=converted)
