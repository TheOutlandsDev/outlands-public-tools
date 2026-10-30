"""Convert explicitly declared boxes without clipping or rounding pixel edges."""
import toolkit as t
import decision_core as c
import visual_core as v

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','images','boxes'})
    t.require(value['format']=='outlands-bounding-box-conversion-v1','FORMAT_INVALID')
    counts={};issues=[];images=v.collect(value['images'],v.image,'images',counts,issues)
    boxes=v.collect(value['boxes'],v.box,'boxes',counts,issues)
    for position,row in boxes.values():v.reference(row,images,'boxes',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(boxes.items()):
            image=images[row['image']][1];result=v.convert_box(row,image['width'],image['height'])
            for code in result['failed_criteria']:c.issue(issues,'boxes',position,code)
            outcomes.append(dict(id=key,**result))
        assessment=dict(boxes=outcomes,converted_boxes=sum(r['valid'] for r in outcomes),all_boxes_converted=all(r['valid'] for r in outcomes))
    return v.output(raw,'outlands-bounding-box-conversion-report-v1',counts,issues,assessment=assessment,
        images_sha256=c.cohort_pin(images) if qualified else None,boxes_sha256=c.cohort_pin(boxes) if qualified else None,
        coordinates_clipped=False,coordinates_rounded=False)

def main(argv=None):return c.cli('Convert explicit box conventions exactly; no asset updates or export.',check,argv)
if __name__=='__main__':raise SystemExit(main())
