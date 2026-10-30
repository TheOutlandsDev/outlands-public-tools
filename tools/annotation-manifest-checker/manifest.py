"""Check declared image, taxonomy and annotation snapshot references."""
import toolkit as t
import decision_core as c
import visual_core as v

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','images','annotations'})
    t.require(value['format']=='outlands-annotation-manifest-v1','FORMAT_INVALID')
    counts={};issues=[];taxonomy,images,annotations=v.scope(value,counts,issues);qualified=not issues;assessment=None
    if qualified:
        per_image=[dict(id=key,annotations=sum(r['image']==key for _,r in annotations.values())) for key in sorted(images)]
        unused=[r['id'] for r in per_image if r['annotations']==0]
        if unused:c.issue(issues,'images',0,'IMAGES_UNANNOTATED')
        assessment=dict(images=len(images),annotations=len(annotations),per_image=per_image,unannotated_images=unused,
                        label_counts={label:sum(r['label']==label for _,r in annotations.values()) for label in taxonomy['labels']})
    return v.output(raw,'outlands-annotation-manifest-report-v1',counts,issues,assessment=assessment,geometry_verified=False,
        images_sha256=c.cohort_pin(images) if qualified else None,annotations_sha256=c.cohort_pin(annotations) if qualified else None,
        taxonomy_sha256=c.pin(taxonomy) if qualified else None)

def main(argv=None):return c.cli('Check declared annotation references; never read images or verify geometry.',check,argv)
if __name__=='__main__':raise SystemExit(main())
