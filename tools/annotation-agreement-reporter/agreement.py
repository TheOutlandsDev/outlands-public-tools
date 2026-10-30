"""Report categorical review agreement with explicit missing-review accounting."""
from collections import defaultdict
from itertools import combinations
import toolkit as t
import decision_core as c
import dataset_common as d

def item(row):return c.record(row,{'id','revision'},('id',),('revision',))

def review(row):return c.record(row,{'id','item','item_revision','reviewer','label'},('id','item','reviewer','label'),('item_revision',))

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','items','reviewers','reviews'})
    t.require(value['format']=='outlands-annotation-agreement-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['taxonomy']);reviewers=c.tags(value['reviewers'],2);counts={};issues=[]
    items=d.collect(value['items'],item,'items',counts,issues,True)
    reviews=d.collect(value['reviews'],d.with_labels(review,taxonomy['labels']),'reviews',counts,issues)
    slots=d.unique_slot(reviews,lambda r:(r['item'],r['reviewer']),'reviews',issues)
    for position,row in reviews.values():
        target=items.get(row['item'])
        if target is None:c.issue(issues,'reviews',position,'ITEM_UNKNOWN')
        elif target[1]['revision']!=row['item_revision']:c.issue(issues,'reviews',position,'ITEM_REVISION_MISMATCH')
        if row['reviewer'] not in reviewers:c.issue(issues,'reviews',position,'REVIEWER_UNKNOWN')
    qualified=not issues;assessment=None
    if qualified:
        by_item=defaultdict(dict)
        for (key,reviewer),row in slots.items():by_item[key][reviewer]=row['label']
        outcomes=[];missing=complete=disagreements=0
        for key in sorted(items):
            selected=by_item[key];absent=sorted(set(reviewers)-set(selected));labels=sorted(set(selected.values()))
            missing+=len(absent);complete+=not absent;disagreements+=len(labels)>1
            outcomes.append(dict(id=key,reviewed_count=len(selected),missing_reviewers=absent,labels=labels,
                                 unanimous=len(labels)==1 if len(selected)>=2 else None))
        pairs=[];matched=agree=0
        for left,right in combinations(reviewers,2):
            shared=[r for r in by_item.values() if left in r and right in r]
            n=len(shared);same=sum(r[left]==r[right] for r in shared);matched+=n;agree+=same
            pairs.append(dict(left=left,right=right,matched_items=n,agreements=same,disagreements=n-same,
                              agreement=c.ratio(same,n) if n else None))
        if missing:c.issue(issues,'reviews',0,'REVIEWS_MISSING')
        if disagreements:c.issue(issues,'reviews',0,'LABEL_DISAGREEMENTS')
        assessment=dict(items=outcomes,reviewed_slots=len(slots),expected_slots=len(items)*len(reviewers),missing_slots=missing,
            complete_items=complete,disagreement_items=disagreements,pairs=pairs,matched_pairs=matched,agreeing_pairs=agree,
            pair_weighted_agreement=c.ratio(agree,matched) if matched else None)
    return d.output(raw,'outlands-annotation-agreement-report-v1',counts,issues,assessment=assessment,
                    items_sha256=c.cohort_pin(items) if qualified else None,taxonomy_sha256=c.pin(taxonomy) if qualified else None)

def main(argv=None):return c.cli('Compare explicit categorical reviews; no adjudication or truth claim.',check,argv)
if __name__=='__main__':raise SystemExit(main())
