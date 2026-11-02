"""Exact local route/fragment declarations; no browser, HTML, network or execution."""
import re
import toolkit as t
import decision_core as c

def path(value):
    t.require(type(value) is str and 1<=len(value)<=256,'LOCAL_PATH_INVALID')
    if value=='/':return value
    parts=value.split('/');t.require(parts[0]=='' and 1<=len(parts)-1<=8,'LOCAL_PATH_INVALID')
    t.require(all(re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}',part) for part in parts[1:]),'LOCAL_PATH_INVALID');return value

def ids(value,maximum,minimum=0):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'ID_LIST_LIMIT')
    for v in value:t.identifier(v)
    t.require(len(value)==len(set(value)),'NESTED_ID_DUPLICATE');return sorted(value)

def nested(value,parser,maximum,minimum=1):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT');seen=set();out=[]
    for row in value:
        key,normalized=parser(row);t.require(key not in seen,'NESTED_ID_DUPLICATE');seen.add(key);out.append(normalized)
    return sorted(out,key=lambda row:row['id'])

def route(row):
    key,out=c.record(row,{'id','path','kind','page','redirect_to','anchors'},('id',));path(row['path']);out['anchors']=ids(row['anchors'],32)
    t.require(row['kind'] in ('page','redirect'),'ROUTE_KIND_INVALID')
    if row['kind']=='page':t.identifier(row['page']);t.require(row['redirect_to'] is None,'PAGE_REDIRECT_INVALID')
    else:t.identifier(row['redirect_to']);t.require(row['page'] is None and not row['anchors'],'REDIRECT_PAYLOAD_INVALID')
    return key,out

def chain(manifest,route_id):
    records={v['id']:v for v in manifest['routes']};seen=set();out=[];selected=route_id
    while True:
        t.require(selected in records,'REDIRECT_REFERENCE_UNKNOWN');t.require(selected not in seen,'REDIRECT_CYCLE');seen.add(selected);out.append(selected);row=records[selected]
        if row['kind']=='page':return row,out
        selected=row['redirect_to']

def manifest(row):
    key,out=c.record(row,{'id','revision','routes'},('id',),('revision',));out['routes']=nested(row['routes'],route,128)
    t.require(len({v['path'] for v in out['routes']})==len(out['routes']),'ROUTE_PATH_DUPLICATE')
    pages=[v['page'] for v in out['routes'] if v['kind']=='page'];t.require(bool(pages),'PAGE_REQUIRED');t.require(len(set(pages))==len(pages),'PAGE_ID_DUPLICATE')
    for v in out['routes']:chain(out,v['id'])
    return key,out

def link(row):
    key,out=c.record(row,{'id','revision','manifest','manifest_revision','manifest_sha256','source','target_path','fragment'},('id','manifest','source'),('revision','manifest_revision'));t.sha(row['manifest_sha256']);path(row['target_path'])
    if row['fragment'] is not None:t.identifier(row['fragment'])
    return key,out

def plan(row):
    key,out=c.record(row,{'id','revision','manifest','manifest_revision','manifest_sha256','links_sha256','starts'},('id','manifest'),('revision','manifest_revision'));t.sha(row['manifest_sha256']);t.sha(row['links_sha256']);out['starts']=ids(row['starts'],32,1);return key,out

def collect(value,parser,side,counts,issues,required=True,maximum=128):
    t.require(type(value) is list and len(value)<=maximum,'COHORT_LIMIT');rows,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not rows:c.issue(issues,side,0,'COHORT_EMPTY')
    return rows

def reference(row,manifests,side,position,issues):
    target=manifests.get(row['manifest'])
    if target is None:c.issue(issues,side,position,'MANIFEST_UNKNOWN');return None
    selected=target[1]
    if row['manifest_revision']!=selected['revision'] or row['manifest_sha256']!=c.pin(selected):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return selected

def context(value,prefix,counts,issues,plans=False,required_links=True):
    key=lambda name:prefix+name
    manifests=collect(value[key('manifests')],manifest,key('manifests'),counts,issues,True,32)
    links=collect(value[key('links')],link,key('links'),counts,issues,required_links,512);groups={k:{} for k in manifests}
    for name,(position,row) in sorted(links.items()):
        target=reference(row,manifests,key('links'),position,issues)
        if target:
            groups[row['manifest']][name]=(position,row);source=next((v for v in target['routes'] if v['id']==row['source']),None)
            if source is None or source['kind']!='page':c.issue(issues,key('links'),position,'SOURCE_PAGE_UNKNOWN')
    result=dict(manifests=manifests,links=links,groups=groups)
    if plans:
        selected=collect(value['plans'],plan,'plans',counts,issues,True,32)
        for _,(position,row) in sorted(selected.items()):
            target=reference(row,manifests,'plans',position,issues)
            if target:
                if row['links_sha256']!=c.cohort_pin(groups[row['manifest']]):c.issue(issues,'plans',position,'LINK_COHORT_MISMATCH')
                known={v['id'] for v in target['routes']}
                if not set(row['starts'])<=known:c.issue(issues,'plans',position,'START_ROUTE_UNKNOWN')
        result['plans']=selected
    return result

def resolve(manifest,target_path,fragment):
    initial=next((v for v in manifest['routes'] if v['path']==target_path),None)
    result=dict(state='path_unknown',terminal_route=None,page=None,fragment=None,redirect_chain=[])
    if initial is None:return result
    terminal,steps=chain(manifest,initial['id']);result.update(state='valid',terminal_route=terminal['id'],page=terminal['page'],redirect_chain=steps)
    if fragment is not None:
        if fragment not in terminal['anchors']:result['state']='fragment_unknown'
        else:result['fragment']=fragment
    return result

def link_outcome(row,manifest):
    result=resolve(manifest,row['target_path'],row['fragment']);result['id']=row['id'];result['source_page']=next(v['page'] for v in manifest['routes'] if v['id']==row['source']);return result

def outcomes(scope):return {k:link_outcome(row,scope['manifests'][row['manifest']][1]) for k,(_,row) in sorted(scope['links'].items())}

def graph(manifest,links,starts):
    pages={v['page'] for v in manifest['routes'] if v['kind']=='page'};edges={k:set() for k in pages}
    for row in links:edges[row['source_page']].add(row['page'])
    start_pages=sorted({chain(manifest,k)[0]['page'] for k in starts})
    def closure(start):
        found={start};pending=[start]
        while pending:
            current=pending.pop()
            for target in sorted(edges[current]-found):found.add(target);pending.append(target)
        return found
    closures={k:closure(k) for k in sorted(pages)};reachable=set().union(*(closures[k] for k in start_pages));remaining=set(pages);components=[]
    while remaining:
        seed=min(remaining);members={k for k in remaining if k in closures[seed] and seed in closures[k]};remaining-=members
        if len(members)>1 or seed in edges[seed]:components.append(sorted(members))
    return dict(start_pages=start_pages,reachable_pages=sorted(reachable),unreachable_pages=sorted(pages-reachable),dead_end_pages=sorted(k for k in reachable if not edges[k]),navigation_cycles=sorted(components),unique_edge_count=sum(map(len,edges.values())))

def output(raw,mode,counts,issues,assessment,pins):
    out=c.base(raw,'outlands-navigation-'+mode+'-report-v1',counts,issues);qualified=assessment is not None
    out.update(assessment=assessment,cohort_sha256=pins if qualified else None,qualified_scope_sha256=c.pin(pins) if qualified and not issues else None,browser_started=False,dom_inspected=False,network_requests_performed=False,records_changed=False,whole_site_compatibility_verified=False,accessibility_verified=False)
    return out

def check(raw,mode):
    value=t.decode(raw);fields={'routes':{'manifests'},'targets':{'manifests','links'},'reachability':{'manifests','links','plans'},'scenarios':{'baseline_manifests','candidate_manifests','baseline_links','candidate_links'}}[mode]
    t.fields(value,fields|{'format'});t.require(value['format']=='outlands-navigation-'+mode+'-v1','FORMAT_INVALID');counts={};issues=[];assessment=None;pins={}
    if mode=='routes':
        manifests=collect(value['manifests'],manifest,'manifests',counts,issues,True,32);pins['manifests']=c.cohort_pin(manifests)
        if not issues:assessment=dict(manifests=[dict(id=k,revision=v['revision'],sha256=c.pin(v),page_count=sum(r['kind']=='page' for r in v['routes']),redirect_count=sum(r['kind']=='redirect' for r in v['routes'])) for k,(_,v) in sorted(manifests.items())])
    elif mode in ('targets','reachability'):
        scope=context(value,'',counts,issues,mode=='reachability',mode=='targets');pins={k:c.cohort_pin(scope[k]) for k in ('manifests','links')+(('plans',) if mode=='reachability' else ())}
        if not issues:
            results=outcomes(scope);assessment=dict(links=list(results.values()))
            for k,(position,row) in sorted(scope['links'].items()):
                if results[k]['state']!='valid':c.issue(issues,'links',position,'TARGET_UNRESOLVED')
            if mode=='reachability':
                plans=[]
                for k,(position,row) in sorted(scope['plans'].items()):
                    group=[results[name] for name in sorted(scope['groups'][row['manifest']])];complete=all(v['state']=='valid' for v in group);result=dict(id=k,complete=complete,graph=graph(scope['manifests'][row['manifest']][1],group,row['starts']) if complete else None);plans.append(result)
                    if not complete:c.issue(issues,'plans',position,'GRAPH_WITHHELD_BROKEN_TARGET')
                    elif result['graph']['unreachable_pages']:c.issue(issues,'plans',position,'UNREACHABLE_PAGES')
                assessment['plans']=plans
    else:
        before=context(value,'baseline_',counts,issues);after=context(value,'candidate_',counts,issues,required_links=False)
        pins={prefix+key:c.cohort_pin(scope[key]) for prefix,scope in [('baseline_',before),('candidate_',after)] for key in ('manifests','links')}
        for k in before['manifests'].keys()&after['manifests'].keys():
            a=before['manifests'][k][1];b=after['manifests'][k][1]
            if a['revision']==b['revision'] and c.pin(a)!=c.pin(b):c.issue(issues,'candidate_manifests',after['manifests'][k][0],'SAME_REVISION_DEFINITION_CONFLICT')
        if not issues:
            a=outcomes(before);b=outcomes(after);comparisons=[]
            def observation(row):return {k:v for k,v in row.items() if k not in ('manifest','manifest_revision','manifest_sha256')}
            for position,k in enumerate(sorted(a.keys()|b.keys()),1):
                left=a.get(k);right=b.get(k);state='equal';comparable=False;equal=False
                if left is None:state='baseline_missing'
                elif right is None:state='candidate_missing'
                elif observation(before['links'][k][1])!=observation(after['links'][k][1]):state='observation_changed'
                else:
                    comparable=True;equal=left['state']==right['state']=='valid' and left==right
                    if left['state']!='valid' or right['state']!='valid':state='invalid_target'
                    elif not equal:state='outcome_changed'
                comparisons.append(dict(id=k,state=state,comparable=comparable,equal=equal,baseline=left if comparable else None,candidate=right if comparable else None))
                if not equal:c.issue(issues,'scenarios',position,'NAVIGATION_SCENARIO_MISMATCH')
            assessment=dict(links=comparisons,all_selected_outcomes_equal=all(v['equal'] for v in comparisons))
    return output(raw,mode,counts,issues,assessment,pins)
