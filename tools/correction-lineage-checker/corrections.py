"""Check explicitly supplied full correction histories; never apply corrections."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import review_core as r

def snapshot(row):
    key,out=c.record(row,{'id','record','revision','artifact_sha256'},('id','record'),('revision',));t.sha(row['artifact_sha256']);return key,out

def correction(row):
    key,out=c.record(row,{'id','before','before_revision','before_sha256','after','after_revision','after_sha256'},('id','before','after'),('before_revision','after_revision'))
    t.sha(row['before_sha256']);t.sha(row['after_sha256']);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','snapshots','corrections'});t.require(v['format']=='outlands-correction-lineage-v1','FORMAT_INVALID')
    counts={};issues=[];snapshots=r.collect(v['snapshots'],snapshot,'snapshots',counts,issues)
    corrections=r.collect(v['corrections'],correction,'corrections',counts,issues,False)
    r.slots(snapshots,lambda row:(row['record'],row['revision']),'snapshots',issues)
    r.slots(corrections,lambda row:row['before'],'corrections',issues);r.slots(corrections,lambda row:row['after'],'corrections',issues)
    for position,row in corrections.values():
        before=r.reference(row,'before',snapshots,'corrections',position,issues);after=r.reference(row,'after',snapshots,'corrections',position,issues)
        if before and after:
            if before['record']!=after['record']:c.issue(issues,'corrections',position,'CROSS_RECORD_CHANGE')
            if after['revision']!=before['revision']+1:c.issue(issues,'corrections',position,'NON_SUCCESSOR_REVISION')
            if before['artifact_sha256']==after['artifact_sha256']:c.issue(issues,'corrections',position,'UNCHANGED_ARTIFACT')
    qualified=not issues;assessment=None
    if qualified:
        grouped=defaultdict(list);parents={row['after']:row['id'] for _,row in corrections.values()}
        for key,(position,row) in snapshots.items():grouped[row['record']].append((key,position,row))
        out=[]
        for record,members in sorted(grouped.items()):
            members.sort(key=lambda pair:pair[2]['revision']);expected=1;codes=[]
            for key,position,row in members:
                if row['revision']!=expected:c.issue(issues,'snapshots',position,'REVISION_GAP');codes.append('REVISION_GAP')
                if row['revision']>1 and key not in parents:c.issue(issues,'snapshots',position,'PARENT_CORRECTION_MISSING');codes.append('PARENT_CORRECTION_MISSING')
                expected=row['revision']+1
            out.append(dict(record=record,snapshot_ids=[key for key,_,_ in members],correction_ids=[parents[key] for key,_,_ in members if key in parents],complete_declared_history=not codes,failed_criteria=sorted(set(codes))))
        assessment=dict(records=out,all_histories_complete=not issues)
    return r.output(raw,'outlands-correction-lineage-report-v1',counts,issues,qualified,assessment,dict(snapshots=snapshots,corrections=corrections))

def main(argv=None):return c.cli('Check pinned declared correction histories; no edits applied.',check,argv)
if __name__=='__main__':raise SystemExit(main())
