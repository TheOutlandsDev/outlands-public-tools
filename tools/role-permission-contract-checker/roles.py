"""Check explicit role inheritance and literal permissions without changing access."""
import toolkit as t
import decision_core as c
import access_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','policy'});t.require(v['format']=='outlands-role-permission-contract-v1','FORMAT_INVALID');counts={};issues=[];context=r.policy(v['policy'],'policy',counts,issues);qualified=not issues;assessment=None
    if qualified:
        assessment=dict(roles=[dict(id=key,inherited_role_ids=sorted(context['closure'][key]-{key})) for key in sorted(context['closure'])],actors=[dict(id=key,assigned_role_ids=next(row['roles'] for _,row in context['sets']['assignments'].values() if row['actor']==key),effective_role_ids=sorted(context['actors'][key])) for key in sorted(context['actors'])],inheritance_acyclic=True,permission_values_interpreted=False)
    return r.output(raw,'outlands-role-permission-contract-report-v1',counts,issues,qualified,assessment,dict(policy_sha256=c.pin(context['value'])))

def main(argv=None):return c.cli('Check declared roles and literal permission references; no authentication or changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
