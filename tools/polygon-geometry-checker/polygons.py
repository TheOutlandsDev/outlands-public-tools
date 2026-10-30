"""Inspect explicit simple polygon geometry using bounded exact integer arithmetic."""
import toolkit as t
import decision_core as c
import visual_core as v

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','images','polygons'})
    t.require(value['format']=='outlands-polygon-geometry-v1','FORMAT_INVALID')
    counts={};issues=[];images=v.collect(value['images'],v.image,'images',counts,issues)
    polygons=v.collect(value['polygons'],v.polygon,'polygons',counts,issues);v.vertex_budget(polygons,'vertices')
    for position,row in polygons.values():v.reference(row,images,'polygons',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(polygons.items()):
            image=images[row['image']][1];result=v.analyze_polygon(row['vertices'],image['width'],image['height'])
            for code in result['failed_criteria']:c.issue(issues,'polygons',position,code)
            outcomes.append(dict(id=key,**result))
        assessment=dict(polygons=outcomes,valid_polygons=sum(r['valid'] for r in outcomes),eligible_for_manual_geometry_review=all(r['valid'] for r in outcomes))
    return v.output(raw,'outlands-polygon-geometry-report-v1',counts,issues,assessment=assessment,
        images_sha256=c.cohort_pin(images) if qualified else None,polygons_sha256=c.cohort_pin(polygons) if qualified else None,
        geometry_repaired=False)

def main(argv=None):return c.cli('Inspect declared simple polygons; no repair, masks or image access.',check,argv)
if __name__=='__main__':raise SystemExit(main())
