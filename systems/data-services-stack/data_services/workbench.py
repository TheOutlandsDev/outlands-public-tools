"""Serialized browser operations over the unchanged durable stack and fake transport."""
from copy import deepcopy
from dataclasses import asdict
import threading
import uuid
from . import files
from .components.ingestion import ReferenceError,ingest_csv,ingest_jsonl
from .components.outbox import FakeTransport,OutboxError
from .contracts import StackError,canonical,decode,digest,fictional_configuration,fictional_input,integer,token
from .service import _calculate

REVIEW_KEYS={'quality','privacy','rights','context'}
MAX_REPORTS=128

def text(value,maximum=65536):
    if type(value) is not str or len(value)>maximum:raise StackError('TEXT_LIMIT_OR_TYPE')
    try:raw=value.encode('utf-8')
    except UnicodeError:raise StackError('TEXT_ENCODING_INVALID') from None
    if len(raw)>maximum:raise StackError('TEXT_LIMIT_OR_TYPE')
    return raw

def shape(value,keys):
    if type(value) is not dict or set(value)!=set(keys):raise StackError('REQUEST_SCHEMA_INVALID')

class Workbench:
    """One local owner; all operations, including reads, share a lock."""
    def __init__(self,stack,reports):
        self.stack=stack;self.lock=threading.RLock();self.reports=files.selected(reports,output=True)
        if self.reports.is_relative_to(stack.root) or stack.root.is_relative_to(self.reports):raise StackError('REPORT_ROOT_OVERLAPS_WORKSPACE')
        files.mkdir(self.reports)
        self._guard=files.directory(self.reports);self._guard.__enter__();self.count=0
    def close(self):self._guard.__exit__(None,None,None)
    def head(self,expected):
        if expected!=self.stack.status()['head_sha256']:raise StackError('JOURNAL_HEAD_CONFLICT')
    def overview(self):
        return dict(**self.stack.status(),configuration=dict(version=1,jobs=[deepcopy(v) for _,v in sorted(self.stack._state['jobs'].items())]),last_tick=self.stack._state['last_tick'],fictional_dispatch_only=True,real_delivery_verified=False)
    def _preview(self,job_id,content):
        token(job_id);self.stack._ready();raw=text(content)
        if job_id not in self.stack._state['jobs']:raise StackError('JOB_NOT_FOUND')
        spec=self.stack._state['jobs'][job_id];issues=[];points=[];duplicates=0;estimate=None
        try:
            batch=(ingest_csv if spec['input_format']=='csv' else ingest_jsonl)(content)
            points=[asdict(p) for p in batch.records];duplicates=batch.duplicates;issues=[asdict(i) for i in batch.issues]
            if batch.ok:estimate=_calculate(spec,raw)
        except ReferenceError as error:issues.append(dict(record=0,code=str(error)))
        value=dict(job_id=job_id,input_sha256=digest(raw),job_sha256=digest(canonical(spec)),head_sha256=self.stack.head,clean=estimate is not None and not issues,records=points,duplicates=duplicates,issues=issues,estimate=estimate)
        return dict(**value,preview_sha256=digest(canonical(value)))
    def _review(self,value):
        shape(value,('actor','note','checks'))
        actor=text(value['actor'],128).decode().strip();note=text(value['note'],4096).decode().strip();checks=value['checks']
        if not actor or not note or type(checks) is not dict or set(checks)!=REVIEW_KEYS or any(v is not True for v in checks.values()):raise StackError('REVIEW_REQUIRED')
        return dict(actor=actor,note=note,checks=deepcopy(checks),scope='PRIVATE_REPORT_ONLY',public_release_authorized=False)
    def _report(self,data):
        selected=self.stack.result(data['key']);pin=digest(canonical(selected))
        if selected['state']!='COMPLETED':raise StackError('COMPLETED_RUN_REQUIRED')
        if pin!=data['result_sha256']:raise StackError('RESULT_PIN_MISMATCH')
        review=self._review(data['review'])
        if self.count>=MAX_REPORTS:raise StackError('REPORT_CAPACITY')
        folder=self.reports/('report_'+uuid.uuid4().hex);files.mkdir(folder);self.count+=1
        values={'run.json':canonical(selected),'review.json':canonical(dict(**review,key=data['key'],result_sha256=pin,head_sha256=self.stack.head))}
        inventory={}
        for name,raw in values.items():
            files.write_new(folder/name,raw)
            if files.read(folder/name,len(raw))!=raw:raise StackError('REPORT_READBACK_FAILED')
            inventory[name]=dict(bytes=len(raw),sha256=digest(raw))
        manifest=dict(format='outlands-data-services-report-v1',key=data['key'],head_sha256=self.stack.head,result_sha256=pin,files=inventory,private=True,source_input_included=False,real_delivery_verified=False,public_release_authorized=False)
        raw=canonical(manifest);files.write_new(folder/'manifest.json',raw)
        if files.read(folder/'manifest.json',len(raw))!=raw:raise StackError('REPORT_READBACK_FAILED')
        return dict(directory=folder.name,manifest=manifest)
    def apply(self,operation,data):
        with self.lock:
            if operation=='overview':shape(data,());return self.overview()
            if operation=='fixtures':
                shape(data,());return dict(configuration=decode(fictional_configuration()),jsonl=fictional_input().decode(),csv='series,period,value\n'+''.join('sample,'+str(i)+','+str(2*(i+1))+'\n' for i in range(6)))
            if operation=='inspect':
                shape(data,('key',));value=self.stack.result(data['key']);return dict(key=data['key'],run=value,result_sha256=digest(canonical(value)),head_sha256=self.stack.head)
            schemas={'configure':('expected_head','configuration'),'preview':('expected_head','job_id','content'),'run':('expected_head','job_id','key','content','preview_sha256'),'dispatch':('expected_head','now','limit','outcomes'),'report-delivery':('expected_head','key','receipt','assertion'),'export':('expected_head','key','result_sha256','review'),'shutdown':('expected_head',)}
            if operation not in schemas:raise StackError('OPERATION_REFUSED')
            shape(data,schemas[operation])
            # Stopping the owned service writes no journal state and must remain
            # possible after an uncertain write poisons the stack session.
            if operation=='shutdown':return dict(state='STOPPING')
            self.head(data['expected_head'])
            if operation=='configure':return self.stack.configure(text(data['configuration']))
            if operation=='preview':return self._preview(data['job_id'],data['content'])
            if operation=='run':
                preview=self._preview(data['job_id'],data['content'])
                if preview['preview_sha256']!=data['preview_sha256']:raise StackError('PREVIEW_PIN_MISMATCH')
                if not preview['clean']:raise StackError('BATCH_REVIEW_REQUIRED')
                return self.stack.run(data['job_id'],data['key'],text(data['content']))
            if operation=='dispatch':
                outcomes=data['outcomes']
                if type(outcomes) is not list or len(outcomes)>64:raise StackError('FAKE_PARAMETER_INVALID')
                try:transport=FakeTransport(outcomes=tuple(outcomes))
                except OutboxError:raise StackError('FAKE_PARAMETER_INVALID') from None
                try:result=self.stack.dispatch(transport,now=data['now'],limit=data['limit'])
                except KeyboardInterrupt:return dict(state='INTERRUPTED_REVIEW_REQUIRED',queue=self.stack.queue(),fake_calls=transport.calls,real_delivery_verified=False)
                return dict(state='FICTIONAL_DISPATCH_COMPLETE',queue=result,fake_calls=transport.calls,real_delivery_verified=False)
            if operation=='report-delivery':
                if data['assertion'] is not True:raise StackError('DELIVERY_ASSERTION_REQUIRED')
                return dict(**self.stack.report_delivery(data['key'],data['receipt']),real_delivery_verified=False)
            if operation=='export':return self._report(data)
            return dict(state='STOPPING')
