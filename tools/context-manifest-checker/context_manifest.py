"""Validate exact supplied document pins and dependency relationships, offline."""
import toolkit as t
import knowledge_core as c


def relationship(row):
    t.fields(row,{'dependent','prerequisite'})
    a=c.reference(row['dependent']); b=c.reference(row['prerequisite'])
    t.require(a['id']!=b['id'],'SELF_DEPENDENCY')
    return (a['id'],b['id']),dict(dependent=a,prerequisite=b)


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','documents','relationships'})
    t.require(value['format']=='outlands-context-manifest-v1','FORMAT_INVALID')
    docs,dc,issues=c.documents(value['documents'])
    edges,ec,other=c.rows(value['relationships'],relationship,'relationships'); issues+=other
    c.nonempty(docs,issues,'documents')
    graph={key:set() for key in docs}
    for index,row in edges.values():
        def bind():
            c.resolve(row['dependent'],docs); c.resolve(row['prerequisite'],docs)
            graph[row['dependent']['id']].add(row['prerequisite']['id'])
        c.issue(issues,'relationships',index,bind)
    # Bounded Kahn ordering avoids recursive depth behavior. Cycles never produce a partial plan.
    order=[]; remaining={key:set(deps) for key,deps in graph.items()}
    while remaining:
        ready=sorted(key for key,deps in remaining.items() if not deps)
        if not ready:
            issues.append(dict(side='relationships',row=0,code='DEPENDENCY_CYCLE')); break
        order+=ready
        for key in ready: del remaining[key]
        for deps in remaining.values(): deps.difference_update(ready)
    result=c.base(raw,'outlands-context-manifest-review-v1',dict(documents=dc,relationships=ec),issues)
    manifest=None
    if not issues:
        manifest=dict(documents=[dict(id=key,revision=docs[key][1]['revision'],sha256=docs[key][1]['sha256'],
                       characters=len(docs[key][1]['text']),utf8_bytes=len(docs[key][1]['text'].encode('utf-8')))
                     for key in sorted(docs)],relationships=[edges[key][1] for key in sorted(edges)])
    result.update(manifest=manifest,manifest_sha256=t.digest(t.encode(manifest)) if manifest is not None else None,
                  dependency_order=order if not issues else None,execution_performed=False)
    return result


def main(argv=None): return c.cli('Check supplied context document pins and relationships.',check,argv)
if __name__=='__main__': raise SystemExit(main())
