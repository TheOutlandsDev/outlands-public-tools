"""Plan downstream rechecks in an explicitly pinned acyclic graph; no discovery."""
from collections import defaultdict, deque
import toolkit as t
import decision_core as c
import review_core as r

def dependency(row):
    key,out=c.record(row,{'id','upstream','upstream_revision','upstream_sha256','downstream','downstream_revision','downstream_sha256'},('id','upstream','downstream'),('upstream_revision','downstream_revision'))
    t.sha(row['upstream_sha256']);t.sha(row['downstream_sha256']);return key,out

def change(row):
    key,out=c.record(row,{'id','node','node_revision','node_sha256'},('id','node'),('node_revision',));t.sha(row['node_sha256']);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','nodes','dependencies','changes'});t.require(v['format']=='outlands-change-impact-v1','FORMAT_INVALID')
    counts={};issues=[];nodes=r.collect(v['nodes'],r.snapshot,'nodes',counts,issues)
    dependencies=r.collect(v['dependencies'],dependency,'dependencies',counts,issues,False)
    changes=r.collect(v['changes'],change,'changes',counts,issues)
    r.slots(dependencies,lambda row:(row['upstream'],row['downstream']),'dependencies',issues);r.slots(changes,lambda row:row['node'],'changes',issues)
    graph=defaultdict(set);indegree={key:0 for key in nodes}
    for position,row in dependencies.values():
        up=r.reference(row,'upstream',nodes,'dependencies',position,issues);down=r.reference(row,'downstream',nodes,'dependencies',position,issues)
        if up and down and row['downstream'] not in graph[row['upstream']]:graph[row['upstream']].add(row['downstream']);indegree[row['downstream']]+=1
    for position,row in changes.values():r.reference(row,'node',nodes,'changes',position,issues)
    queue=deque(sorted(key for key,degree in indegree.items() if degree==0));order=[]
    while queue:
        key=queue.popleft();order.append(key)
        for child in sorted(graph[key]):
            indegree[child]-=1
            if indegree[child]==0:queue.append(child)
    if len(order)!=len(nodes):c.issue(issues,'dependencies',0,'DEPENDENCY_CYCLE')
    qualified=not issues;assessment=None
    if qualified:
        roots=sorted(row['node'] for _,row in changes.values());causes={key:set() for key in nodes}
        for root in roots:causes[root].add(root)
        cause_pairs=len(roots)
        for key in order:
            for child in graph[key]:
                previous=len(causes[child]);causes[child].update(causes[key]);cause_pairs+=len(causes[child])-previous
                t.require(cause_pairs<=50000,'IMPACT_CAUSE_LIMIT')
        assessment=dict(changed_node_ids=roots,recheck_nodes=[dict(id=key,caused_by=sorted(causes[key]),directly_changed=key in roots) for key in sorted(nodes) if causes[key]],
            unaffected_node_ids=sorted(key for key in nodes if not causes[key]),dependency_discovery_complete=False)
    return r.output(raw,'outlands-change-impact-report-v1',counts,issues,qualified,assessment,dict(nodes=nodes,dependencies=dependencies,changes=changes))

def main(argv=None):return c.cli('Plan declared downstream rechecks; no discovery or updates.',check,argv)
if __name__=='__main__':raise SystemExit(main())
