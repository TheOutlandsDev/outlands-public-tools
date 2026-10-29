"""Build a path-free manifest from explicit bounded artifact buffers."""
import toolkit as t
import run_core as c


def selection(raw):
    value=t.decode(raw)
    t.fields(value,{'format','run_id','artifacts'})
    t.require(value['format']=='outlands-run-artifact-selection-v1','SELECTION_FORMAT_INVALID')
    t.identifier(value['run_id'])
    rows=c.items(value['artifacts'],{'id','role'})
    for row in rows.values():
        t.require(type(row['role']) is str and row['role'] in c.ROLES,'ROLE_INVALID')
    return value,rows


def build(selection_raw,inputs):
    value,rows=selection(selection_raw); c.buffers(inputs,rows)
    result=dict(format='outlands-run-artifact-manifest-v1',run_id=value['run_id'],artifacts=[
        dict(id=key,role=rows[key]['role'],bytes=len(inputs[key]),sha256=t.digest(inputs[key]))
        for key in sorted(rows)])
    c.manifest(t.encode(result))
    return dict(status='PASS',format='outlands-run-artifact-build-v1',
                selection_sha256=t.digest(selection_raw),manifest=result,
                manifest_sha256=t.digest(t.encode(result)),
                source_paths_recorded=False,content_privacy_verified=False,target_changes_performed=False)


def main(argv=None):
    p=t.Parser(description='Build a manifest from explicit ID/file bindings; never enumerate a directory.')
    p.add_argument('--selection',required=True)
    p.add_argument('--item',nargs=2,action='append',default=[],metavar=('ID','FILE'))
    p.add_argument('--out')
    def operation(a):
        raw=t.read(a.selection); _,rows=selection(raw); bound=t.bindings(a.item)
        t.require(set(bound)==set(rows),'BINDING_COVERAGE_INVALID')
        return build(raw,t.buffers(bound))
    return t.run(p,operation,argv)


if __name__=='__main__': raise SystemExit(main())
