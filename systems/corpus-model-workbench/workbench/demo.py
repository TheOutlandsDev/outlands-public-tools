"""Fictional client and complete authored workflow; no model service or code execution."""
import json

from . import corpus,models,runtime


class FictionalClient:
    fictional_demo=True
    def __init__(self):self.calls=dict(tags=0,chat=0,embed=0)
    def request(self,endpoint,payload):
        if endpoint=='/api/tags':
            self.calls['tags']+=1
            return dict(models=[dict(name='fictional-model-a',digest='a'*64,details={}),dict(name='fictional-model-b',digest='b'*64,details={})])
        if endpoint=='/api/chat':
            self.calls['chat']+=1
            answer=json.dumps(dict(verdict='acceptable',issues=[],checks_to_run=['Independent fictional review'])) if payload.get('format')=='json' else 'Fictional model response. No code or real inference was executed.'
            return dict(done=True,message=dict(content=answer,thinking='not retained'),eval_count=8,eval_duration=1000000)
        if endpoint=='/api/embed':
            self.calls['embed']+=1
            values=payload['input']
            if type(values) is str:values=[values]
            return dict(embeddings=[[float(sum(value.encode())%7+1),float(len(value)%11+1),1.0] for value in values])
        raise runtime.WorkbenchError('FICTIONAL_OPERATION_UNKNOWN')


def run():
    fake=FictionalClient();runtime.set_client(fake)
    models.load_benchmarks()
    imported=corpus.import_jsonl('inbox/sample-corpus.jsonl','fictional-source','Invented fixtures authored for this example')
    selected=corpus.list_records(limit=100)['records']
    for row in selected:
        corpus.review_record(row['id'],'approved','sample_reviewer','Fictional review assertion only',dict(quality=True,privacy=True,rights=True,context=True))
    sft=corpus.export_dataset('sft')
    rag=corpus.export_dataset('rag')
    benchmark=models.benchmark(['fictional-model-a','fictional-model-b'])
    for row in benchmark['runs']:
        if row['model']=='fictional-model-a':models.score(row['id'],3,'sample_reviewer','Invented rubric score, not measured model quality')
    routing=models.recommend('python')
    embedded=corpus.embed_corpus('fictional-model-a')
    found=corpus.semantic_search('Python example','fictional-model-a')
    discussion=models.discuss('Explain a fictional Python function.','fictional-model-a','fictional-model-b','fictional-model-a',rounds=1)
    queued=models.queue_discussion(discussion['id'])
    backup=corpus.backup()
    return dict(mode='FICTIONAL_CORPUS_WORKBENCH_DEMO',imported=imported,status=corpus.status(),
        sft_counts=sft['manifest']['counts'],rag_counts=rag['manifest']['counts'],
        benchmark_runs=len(benchmark['runs']),routing=dict(model=routing['model'],fallback=routing['fallback']),
        embeddings_written=embedded['chunks_written'],search_results=len(found),discussion_turns=len(discussion['turns']),
        discussion_training_status=queued['training_status'],backup_bytes=backup['bytes'],
        fake_client_calls=fake.calls,real_inference_verified=False,generated_code_executed=False)
