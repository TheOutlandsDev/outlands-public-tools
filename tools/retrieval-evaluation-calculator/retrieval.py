"""Exact macro precision@k, recall@k and reciprocal rank on supplied judgments."""
from fractions import Fraction
import toolkit as t
import knowledge_core as c


def query(row):
    t.fields(row,{'id','ranked','relevant'}); t.identifier(row['id'])
    return row['id'],dict(id=row['id'],ranked=c.references(row['ranked']),relevant=c.references(row['relevant']))


def calculate(raw):
    value=t.decode(raw); t.fields(value,{'format','documents','queries','k'})
    t.require(value['format']=='outlands-retrieval-evaluation-v1','FORMAT_INVALID')
    k=t.integer(value['k'],100,1)
    docs,dc,issues=c.documents(value['documents']); c.nonempty(docs,issues,'documents')
    queries,qc,other=c.rows(value['queries'],query,'queries',100); issues+=other
    c.nonempty(queries,issues,'queries'); scored=[]
    for key,(index,row) in sorted(queries.items()):
        def score():
            t.require(row['relevant'],'RELEVANCE_JUDGMENTS_MISSING')
            for ref in row['ranked']+row['relevant']: c.resolve(ref,docs)
            relevant={c.ref_key(r) for r in row['relevant']}
            top=row['ranked'][:k]
            hits=[pos for pos,r in enumerate(top,1) if c.ref_key(r) in relevant]
            p=Fraction(len(hits),k); r=Fraction(len(hits),len(relevant)); rr=Fraction(1,hits[0]) if hits else Fraction()
            return dict(id=key,returned=len(row['ranked']),evaluated=len(top),relevant=len(relevant),hits=len(hits),
                        precision_at_k=c.ratio(p),recall_at_k=c.ratio(r),reciprocal_rank_at_k=c.ratio(rr)),(p,r,rr)
        item=c.issue(issues,'queries',index,score)
        if item is not None: scored.append(item)
    metrics=None; per_query=None
    if not issues:
        n=len(scored)
        metrics={label:c.ratio(sum((item[1][i] for item in scored),Fraction())/n)
                 for i,label in enumerate(('macro_precision_at_k','macro_recall_at_k','mean_reciprocal_rank_at_k'))}
        per_query=[item[0] for item in scored]
    result=c.base(raw,'outlands-retrieval-metrics-v1',dict(documents=dc,queries=qc),issues)
    result.update(k=k,metrics=metrics,per_query=per_query,relevance_authority_verified=False,
                  retrieval_performed=False,model_quality_verified=False)
    return result


def main(argv=None): return c.cli('Calculate exact retrieval metrics from explicit rankings and binary judgments.',calculate,argv)
if __name__=='__main__': raise SystemExit(main())
