"""Pixel-edge integer polygons, exact scanline fill and independent binary masks."""
from fractions import Fraction
from .contracts import integer
from .runtime import WorkbenchError


def _orientation(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _on(a,b,c):return _orientation(a,b,c)==0 and min(a[0],b[0])<=c[0]<=max(a[0],b[0]) and min(a[1],b[1])<=c[1]<=max(a[1],b[1])
def _intersects(a,b,c,d):
    x,y,z,w=_orientation(a,b,c),_orientation(a,b,d),_orientation(c,d,a),_orientation(c,d,b)
    return x*y<0 and z*w<0 or any((v==0 and _on(p,q,r)) for v,p,q,r in ((x,a,b,c),(y,a,b,d),(z,c,d,a),(w,c,d,b)))


def validate(value,classes,width,height):
    keys={str(row['id']) for row in classes}
    if type(value) is not dict or set(value)!=keys:raise WorkbenchError('POLYGON_CLASS_MAPPING')
    total=0
    for polygons in value.values():
        if type(polygons) is not list or len(polygons)>4:raise WorkbenchError('POLYGON_LIMIT')
        total+=len(polygons)
        for points in polygons:
            if type(points) is not list or not 3<=len(points)<=64:raise WorkbenchError('VERTEX_LIMIT')
            for point in points:
                if type(point) is not list or len(point)!=2:raise WorkbenchError('POINT_INVALID')
                integer(point[0],0,width);integer(point[1],0,height)
            if len({tuple(p) for p in points})!=len(points):raise WorkbenchError('DUPLICATE_VERTEX')
            if sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))==0:raise WorkbenchError('POLYGON_AREA_ZERO')
            for i in range(len(points)):
                a,b=points[i],points[(i+1)%len(points)]
                for j in range(i+1,len(points)):
                    if j==i+1 or i==0 and j==len(points)-1:continue
                    if _intersects(a,b,points[j],points[(j+1)%len(points)]):raise WorkbenchError('POLYGON_SELF_INTERSECTION')
    if total>16:raise WorkbenchError('POLYGON_LIMIT')
    return value


def raster(polygons,width,height):
    mask=bytearray(width*height)
    for points in polygons:
        for y in range(min(p[1] for p in points),max(p[1] for p in points)):
            scan=Fraction(2*y+1,2);intersections=[]
            for i,a in enumerate(points):
                b=points[(i+1)%len(points)]
                if min(a[1],b[1])<=scan<max(a[1],b[1]):intersections.append(Fraction(a[0])+((scan-a[1])*(b[0]-a[0]))/(b[1]-a[1]))
            intersections.sort()
            for i in range(0,len(intersections),2):
                left,right=intersections[i:i+2]
                start=max(0,-((-(left-Fraction(1,2)).numerator)//(left-Fraction(1,2)).denominator))
                end=min(width,-((-(right-Fraction(1,2)).numerator)//(right-Fraction(1,2)).denominator))
                if end>start:mask[y*width+start:y*width+end]=b'\xff'*(end-start)
    return bytes(mask)


def compare(left,right):
    if len(left)!=len(right):raise WorkbenchError('MASK_DIMENSION_MISMATCH')
    intersection=sum(a!=0 and b!=0 for a,b in zip(left,right));union=sum(a!=0 or b!=0 for a,b in zip(left,right));count=sum(a!=0 for a in left)+sum(b!=0 for b in right)
    return dict(intersection=intersection,union=union,iou=intersection/union if union else None,dice=2*intersection/count if count else None,trained_model_evaluated=False)
