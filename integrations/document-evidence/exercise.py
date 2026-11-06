"""Installed fictional document-to-citation workflow; no models or private corpus."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_context_manifest_checker.context_manifest import check as manifest
from outlands_document_chunk_planner.chunks import plan
from outlands_retrieval_evaluation_calculator.retrieval import calculate
from outlands_answer_evidence_checker.evidence import check as evidence

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def ratio(n,d):
    return dict(numerator=str(n),denominator=str(d))

def main():
    body='ABCDEFGHIJK'
    doc=dict(id='sample',revision=3,text=body,sha256=hashlib.sha256(body.encode('utf-8')).hexdigest())
    ref={key:doc[key] for key in ('id','revision','sha256')}
    context=dict(format='outlands-context-manifest-v1',documents=[doc],relationships=[])
    windows=dict(format='outlands-document-chunks-v1',documents=[doc],policy=dict(max_chars=5,overlap_chars=2))
    rankings=dict(format='outlands-retrieval-evaluation-v1',documents=[doc],k=2,queries=[dict(id='query-a',ranked=[ref],relevant=[ref])])
    mr=manifest(raw(context));pr=plan(raw(windows));rr=calculate(raw(rankings))
    assert mr['status']==pr['status']==rr['status']=='PASS'
    assert [(row['start'],row['end']) for row in pr['chunks']]==[(0,5),(3,8),(6,11)]
    selected=pr['chunks'][1]
    assert mr['manifest']['documents'][0]['sha256']==selected['source_sha256']==doc['sha256']
    assert rr['metrics']==dict(macro_precision_at_k=ratio(1,2),macro_recall_at_k=ratio(1,1),mean_reciprocal_rank_at_k=ratio(1,1))
    answer=dict(format='outlands-answer-evidence-v1',documents=[doc],answers=[dict(id='answer-a',text='An invented answer.',citations=[dict(source=ref,start=selected['start'],end=selected['end'],quote=body[selected['start']:selected['end']])])])
    er=evidence(raw(answer));assert er['status']=='PASS'
    assert er['evidence'][0]['checked_citations'][0]['quote_sha256']==selected['sha256']
    assert er['claim_support_verified'] is False and er['factual_truth_verified'] is False
    # Structural citation integrity does not test whether the answer is related.
    unrelated=copy.deepcopy(answer);unrelated['answers'][0]['text']='An unrelated fictional claim.'
    unrelated_report=evidence(raw(unrelated));assert unrelated_report['status']=='PASS' and unrelated_report['claim_support_verified'] is False
    wrong=copy.deepcopy(answer);wrong['answers'][0]['citations'][0]['quote']='WRONG'
    wrong_report=evidence(raw(wrong));assert wrong_report['status']=='REVIEW_REQUIRED' and wrong_report['evidence'] is None
    stale=copy.deepcopy(answer);stale['answers'][0]['citations'][0]['source']['revision']=4
    stale_report=evidence(raw(stale));assert stale_report['status']=='REVIEW_REQUIRED' and stale_report['evidence'] is None
    no_results=copy.deepcopy(rankings);no_results['queries'][0]['ranked']=[]
    zero=calculate(raw(no_results));assert zero['status']=='PASS' and all(v==ratio(0,1) for v in zero['metrics'].values())
    unjudged=copy.deepcopy(rankings);unjudged['queries'][0]['relevant']=[]
    missing=calculate(raw(unjudged));assert missing['status']=='REVIEW_REQUIRED' and missing['metrics'] is None
    other=dict(doc,id='second');other_ref={k:other[k] for k in ('id','revision','sha256')}
    cyclic=dict(format='outlands-context-manifest-v1',documents=[doc,other],relationships=[dict(dependent=ref,prerequisite=other_ref),dict(dependent=other_ref,prerequisite=ref)])
    cycle=manifest(raw(cyclic));assert cycle['status']=='REVIEW_REQUIRED' and cycle['manifest'] is None and cycle['dependency_order'] is None
    fixture=json.loads(files('outlands_retrieval_evaluation_calculator').joinpath('examples','input.json').read_bytes())
    fixture_report=calculate(raw(fixture));assert fixture_report['metrics']==dict(macro_precision_at_k=ratio(1,2),macro_recall_at_k=ratio(3,4),mean_reciprocal_rank_at_k=ratio(3,4))
    # UTF-8 byte length and code-point offsets are distinct for an astral character.
    unicode_doc=dict(id='unicode-sample',revision=1,text='A'+chr(0x1f331)+'BC')
    unicode_doc['sha256']=hashlib.sha256(unicode_doc['text'].encode('utf-8')).hexdigest()
    unicode_report=plan(raw(dict(format='outlands-document-chunks-v1',documents=[unicode_doc],policy=dict(max_chars=2,overlap_chars=0))))
    assert unicode_report['status']=='PASS' and unicode_report['chunks'][0]['characters']==2 and unicode_report['chunks'][0]['utf8_bytes']==5
    for report in (mr,pr,rr,er,unrelated_report,wrong_report,stale_report,zero,missing,cycle,fixture_report,unicode_report):
        assert report['source_authority_verified'] is False and report['content_privacy_verified'] is False and report['target_changes_performed'] is False
        encoded=raw(report)
        for value in (body,answer['answers'][0]['text'],answer['answers'][0]['citations'][0]['quote']):assert value.encode('utf-8') not in encoded
    print(json.dumps(dict(status='PASS',windows=[[0,5],[3,8],[6,11]],precision_at_2=ratio(1,2),citation_pin_matches_chunk=True,unrelated_answer='structural PASS only',wrong_quote='evidence withheld',stale_revision='evidence withheld',missing_judgments='metrics withheld',dependency_cycle='manifest withheld',offset_unit='UNICODE_CODE_POINT',factual_truth_verified=False),sort_keys=True))

if __name__=='__main__':
    main()
