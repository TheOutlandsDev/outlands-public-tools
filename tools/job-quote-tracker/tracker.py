"""Original MIT local Job & Quote Tracker. SQLite persistence, no network calls."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import csv
from datetime import date, datetime, timezone
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import threading
import time
import uuid

VERSION='1.0.0'
APP_ID=0x4F4A5154
MAX_STORE=128*1024*1024
MAX_EXPORT=32*1024*1024
MAX_JOBS=200
MAX_QUOTES=2000
MAX_EVENTS=10000
CURRENCIES={'USD','CAD','EUR','GBP'}
STATES=('new','quoted','approved','scheduled','in_progress','completed','cancelled','archived')
TRANSITIONS={'new':{'cancelled'},'quoted':{'cancelled'},'approved':{'scheduled','cancelled'},
             'scheduled':{'approved','in_progress','cancelled'},'in_progress':{'completed','cancelled'},
             'completed':{'archived'},'cancelled':{'archived'},'archived':set()}
ID=re.compile(r'job-[a-f0-9]{16}\Z')

class TrackerError(ValueError): pass
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def check_cancel(cancel):
    if cancel is not None and cancel.is_set(): raise TrackerError('Operation cancelled; partial new output may remain.')
def text(value,name,limit,required=False):
    if not isinstance(value,str) or len(value)>limit: raise TrackerError(name+': invalid text length/type')
    value=value.strip()
    if required and not value: raise TrackerError(name+': required')
    if any((ord(c)<32 and c not in '\n\t') or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in value): raise TrackerError(name+': control characters or invalid Unicode unsupported')
    return value
def day(value,name='date',required=False):
    value=text(value,name,10,required)
    if value:
        try:
            if date.fromisoformat(value).isoformat()!=value: raise ValueError()
        except ValueError: raise TrackerError(name+': use a real YYYY-MM-DD date') from None
    return value
def job_id(value):
    if not isinstance(value,str) or not ID.fullmatch(value): raise TrackerError('Invalid job ID')
    return value
def amount(value):
    if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9][0-9]{0,6})\.[0-9]{2}',value):
        raise TrackerError('Amount: use 0.00 through 9999999.99 with exactly two decimal places')
    whole,fraction=value.split('.')
    return int(whole)*100+int(fraction)
def display_amount(cents): return f'{cents//100}.{cents%100:02d}'

def validate_version(value):
    if type(value) is not int or value < 1: raise TrackerError('A positive expected version is required; refresh the job first')
    return value
def fields(raw,allowed,required,name):
    if not isinstance(raw,dict) or set(raw)-set(allowed) or not set(required)<=set(raw): raise TrackerError(name+': unexpected/missing fields')
def job_input(raw,partial=False):
    allowed={'title','customer','contact','notes','follow_up'}
    fields(raw,allowed,[] if partial else ['title','customer'],'job')
    if partial and not raw: raise TrackerError('Job edit needs at least one field')
    result={}
    for key,limit in [('title',180),('customer',160),('contact',240),('notes',3000)]:
        if not partial or key in raw: result[key]=text(raw.get(key,''),key,limit,key in ['title','customer'])
    if not partial or 'follow_up' in raw: result['follow_up']=day(raw.get('follow_up',''),'follow_up')
    return result
def quote_input(raw):
    fields(raw,{'amount','currency','scope','exclusions'},['amount','currency','scope'],'quote')
    currency=raw['currency']
    if not isinstance(currency,str) or currency not in CURRENCIES: raise TrackerError('Currency: choose USD, CAD, EUR or GBP')
    return {'amount_cents':amount(raw['amount']),'currency':currency,
            'scope':text(raw['scope'],'scope',3000,True),'exclusions':text(raw.get('exclusions',''),'exclusions',2000)}
def plain_path(value,existing=True):
    path=Path(os.path.abspath(value))
    if str(path).startswith('\\\\'): raise TrackerError('Use trusted local storage, not a UNC path')
    for part in list(path.parents)[::-1]+[path]:
        try: info=part.lstat()
        except FileNotFoundError:
            if existing: raise TrackerError('Selected path or parent does not exist') from None
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(part,'is_junction',lambda:False)(): raise TrackerError('Links/junctions are unsupported')
    return path
def read_json(path):
    path=plain_path(path)
    try:
        if not path.is_file() or path.stat().st_size>65536: raise TrackerError('Input JSON must be a regular file of at most 64 KiB')
        data=path.read_bytes()
        if len(data)>65536: raise TrackerError('Input JSON grew beyond limit')
        def pairs(items):
            result={}
            for key,value in items:
                if key in result: raise TrackerError('Duplicate JSON key')
                result[key]=value
            return result
        value=json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs,
                         parse_int=lambda _: (_ for _ in ()).throw(TrackerError('Input values must be text')),
                         parse_float=lambda _: (_ for _ in ()).throw(TrackerError('Input values must be text')),
                         parse_constant=lambda _: (_ for _ in ()).throw(TrackerError('Nonfinite JSON is unsupported')))
        if not isinstance(value,dict): raise TrackerError('Input JSON must be an object')
        return value
    except (OSError,UnicodeError,json.JSONDecodeError,RecursionError): raise TrackerError('Unreadable or invalid input JSON') from None
def sha(data): return hashlib.sha256(data).hexdigest()
def json_bytes(value): return (json.dumps(value,indent=2,ensure_ascii=True,sort_keys=True)+'\n').encode('utf8')

SCHEMA='''
CREATE TABLE jobs(id TEXT PRIMARY KEY,title TEXT NOT NULL,customer TEXT NOT NULL,contact TEXT NOT NULL,
 notes TEXT NOT NULL,follow_up TEXT NOT NULL,status TEXT NOT NULL,scheduled_date TEXT NOT NULL,
 version INTEGER NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE quotes(job_id TEXT NOT NULL REFERENCES jobs(id),revision INTEGER NOT NULL,amount_cents INTEGER NOT NULL,
 currency TEXT NOT NULL,scope TEXT NOT NULL,exclusions TEXT NOT NULL,created_utc TEXT NOT NULL,
 PRIMARY KEY(job_id,revision));
CREATE TABLE decisions(job_id TEXT NOT NULL,revision INTEGER NOT NULL,decision TEXT NOT NULL,reference TEXT NOT NULL,
 recorded_utc TEXT NOT NULL,PRIMARY KEY(job_id,revision),FOREIGN KEY(job_id,revision) REFERENCES quotes(job_id,revision));
CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL REFERENCES jobs(id),
 action TEXT NOT NULL,detail_json TEXT NOT NULL,recorded_utc TEXT NOT NULL);
CREATE INDEX events_job ON events(job_id,sequence);
CREATE TRIGGER quotes_no_update BEFORE UPDATE ON quotes BEGIN SELECT RAISE(ABORT,'immutable quote revision');END;
CREATE TRIGGER quotes_no_delete BEFORE DELETE ON quotes BEGIN SELECT RAISE(ABORT,'immutable quote revision');END;
CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'immutable decision');END;
CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'immutable decision');END;
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable activity record');END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable activity record');END;
'''
def check_schema(db,integrity=False):
    if db.execute('PRAGMA application_id').fetchone()[0]!=APP_ID or db.execute('PRAGMA user_version').fetchone()[0]!=1:
        raise TrackerError('This file is not a supported Job & Quote Tracker store')
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    if tables!={'jobs','quotes','decisions','events'}: raise TrackerError('Store schema is incomplete or unexpected')
    if integrity:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise TrackerError('Store integrity check failed')

class Store:
    def __init__(self,path):
        self.path=plain_path(path)
        if not self.path.is_file() or self.path.stat().st_size>MAX_STORE: raise TrackerError('Store must be a regular local file no larger than 128 MiB')
        with self.connection(readonly=True) as db: check_schema(db)
    @classmethod
    def create(cls,path):
        path=plain_path(path,False);plain_path(path.parent)
        if path.suffix.lower()!='.sqlite': raise TrackerError('Choose a new .sqlite store file')
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600);os.close(fd)
            db=sqlite3.connect(path,isolation_level=None)
            try:
                db.execute('PRAGMA foreign_keys=ON');db.execute(f'PRAGMA application_id={APP_ID}');db.execute('PRAGMA user_version=1')
                db.executescript(SCHEMA)
            finally:db.close()
        except OSError: raise TrackerError('Store creation failed; existing files are never replaced') from None
        except sqlite3.Error: raise TrackerError('Store initialization failed; a partial new file may remain') from None
        return cls(path)
    @contextmanager
    def connection(self,readonly=False,write=False):
        plain_path(self.path)
        if not self.path.is_file() or self.path.stat().st_size>MAX_STORE: raise TrackerError('Store file is unavailable or over its size limit')
        db=None
        try:
            db=sqlite3.connect(self.path.as_uri()+('?mode=ro' if readonly else '?mode=rw'),uri=True,timeout=5,isolation_level=None)
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA trusted_schema=OFF')
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1024*1024)
            check_schema(db)
            if write: db.execute('BEGIN IMMEDIATE')
            elif readonly: db.execute('BEGIN')
            yield db
            if db.in_transaction: db.commit()
        except sqlite3.Error:
            if db is not None and db.in_transaction: db.rollback()
            raise TrackerError('Database operation failed; it may be busy, damaged or incompatible') from None
        except Exception:
            if db is not None and db.in_transaction: db.rollback()
            raise
        finally:
            if db is not None: db.close()
    @staticmethod
    def existing(db,identity,expected=None):
        row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id(identity),)).fetchone()
        if row is None: raise TrackerError('Job not found')
        if expected is not None and (type(expected) is not int or expected<1 or row['version']!=expected):
            raise TrackerError('Job changed since you loaded it; refresh and review before saving')
        return dict(row)
    @staticmethod
    def event(db,identity,action,detail):
        if db.execute('SELECT COUNT(*) FROM events').fetchone()[0]>=MAX_EVENTS: raise TrackerError('Activity limit reached; create a verified backup and a new working store')
        db.execute('INSERT INTO events(job_id,action,detail_json,recorded_utc) VALUES(?,?,?,?)',(identity,action,json.dumps(detail,sort_keys=True),now()))
    @staticmethod
    def change(db,identity,updates):
        allowed={'title','customer','contact','notes','follow_up','status','scheduled_date'}
        if set(updates)-allowed: raise TrackerError('Unsupported job update')
        columns=','.join(key+'=?' for key in updates)
        db.execute('UPDATE jobs SET '+columns+',version=version+1,updated_utc=? WHERE id=?',(*updates.values(),now(),identity))
    def new_job(self,raw):
        data=job_input(raw);identity='job-'+uuid.uuid4().hex[:16];stamp=now()
        with self.connection(write=True) as db:
            if db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]>=MAX_JOBS: raise TrackerError('Store is limited to 200 jobs including archived records')
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(identity,data['title'],data['customer'],data['contact'],data['notes'],data['follow_up'],'new','',1,stamp,stamp))
            self.event(db,identity,'job_created',{})
        return self.get(identity)
    def edit_job(self,identity,raw,expected_version):
        expected_version = validate_version(expected_version)
        data=job_input(raw,True)
        with self.connection(write=True) as db:
            job=self.existing(db,identity,expected_version)
            if job['status']=='archived': raise TrackerError('Archived jobs are read-only')
            self.change(db,identity,data);self.event(db,identity,'job_details_changed',{'fields':sorted(data)})
        return self.get(identity)
    def add_quote(self,identity,raw,expected_version):
        expected_version = validate_version(expected_version)
        data=quote_input(raw)
        with self.connection(write=True) as db:
            job=self.existing(db,identity,expected_version)
            if job['status'] not in {'new','quoted','approved','scheduled'}: raise TrackerError('Quote revisions require a new, quoted, approved or scheduled job')
            revision=db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM quotes WHERE job_id=?',(identity,)).fetchone()[0]
            if revision>50 or db.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]>=MAX_QUOTES: raise TrackerError('Quote revision limit reached')
            db.execute('INSERT INTO quotes VALUES(?,?,?,?,?,?,?)',(identity,revision,data['amount_cents'],data['currency'],data['scope'],data['exclusions'],now()))
            self.change(db,identity,{'status':'quoted','scheduled_date':''})
            self.event(db,identity,'quote_revision_added',{'revision':revision,'previous_approval_and_schedule_apply':False})
        return self.get(identity)
    @staticmethod
    def current_quote(db,identity):
        row=db.execute('SELECT * FROM quotes WHERE job_id=? ORDER BY revision DESC LIMIT 1',(identity,)).fetchone()
        return dict(row) if row else None
    def decide(self,identity,decision,reference,expected_version):
        expected_version = validate_version(expected_version)
        if decision not in ('approved','rejected'): raise TrackerError('Decision must be approved or rejected')
        reference=text(reference,'Decision reference',1000,True)
        with self.connection(write=True) as db:
            job=self.existing(db,identity,expected_version);quote=self.current_quote(db,identity)
            if job['status'] not in {'quoted','approved','scheduled'} or not quote: raise TrackerError('A current editable quote is required')
            if db.execute('SELECT 1 FROM decisions WHERE job_id=? AND revision=?',(identity,quote['revision'])).fetchone():
                raise TrackerError('This revision already has a recorded decision; add a new revision to correct it')
            db.execute('INSERT INTO decisions VALUES(?,?,?,?,?)',(identity,quote['revision'],decision,reference,now()))
            self.change(db,identity,{'status':'approved' if decision=='approved' else 'quoted','scheduled_date':''})
            self.event(db,identity,'quote_decision_recorded',{'revision':quote['revision'],'decision':decision})
        return self.get(identity)
    def set_status(self,identity,status,expected_version,scheduled_date=''):
        expected_version = validate_version(expected_version)
        if not isinstance(status,str) or status not in STATES: raise TrackerError('Unknown job status')
        appointment=day(scheduled_date,'scheduled_date',status=='scheduled')
        if status!='scheduled' and appointment: raise TrackerError('Only scheduling accepts an appointment date')
        with self.connection(write=True) as db:
            job=self.existing(db,identity,expected_version)
            if status not in TRANSITIONS[job['status']]: raise TrackerError('That status transition is not permitted')
            if status in {'scheduled','in_progress','completed'}:
                quote=self.current_quote(db,identity)
                accepted=db.execute('SELECT decision FROM decisions WHERE job_id=? AND revision=?',(identity,quote['revision'] if quote else 0)).fetchone()
                if not accepted or accepted[0]!='approved': raise TrackerError('The current quote revision needs a recorded approval')
            updates={'status':status}
            if status=='scheduled': updates['scheduled_date']=appointment
            if status in {'approved','cancelled','archived'}: updates['scheduled_date']=''
            self.change(db,identity,updates);self.event(db,identity,'job_status_changed',{'from':job['status'],'to':status})
        return self.get(identity)
    @staticmethod
    def detail(db,identity):
        job=Store.existing(db,identity)
        job['quotes']=[]
        for row in db.execute('SELECT * FROM quotes WHERE job_id=? ORDER BY revision',(identity,)):
            quote=dict(row);quote['amount']=display_amount(quote['amount_cents'])
            decision=db.execute('SELECT decision,reference,recorded_utc FROM decisions WHERE job_id=? AND revision=?',(identity,quote['revision'])).fetchone()
            quote['decision']=dict(decision) if decision else None;job['quotes'].append(quote)
        job['events']=[dict(x) for x in db.execute('SELECT * FROM events WHERE job_id=? ORDER BY sequence',(identity,))]
        return job
    def get(self,identity):
        with self.connection(readonly=True) as db:return self.detail(db,identity)
    def list_jobs(self,status=None,due_before=None):
        if status is not None and status not in STATES: raise TrackerError('Unknown status filter')
        if due_before is not None: day(due_before,'due_before',True)
        where=[];values=[]
        if status is not None:where.append('status=?');values.append(status)
        if due_before is not None:
            where.append("follow_up<>'' AND follow_up<=? AND status NOT IN ('completed','cancelled','archived')");values.append(due_before)
        query='SELECT * FROM jobs'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY updated_utc DESC,id'
        with self.connection(readonly=True) as db:return [dict(row) for row in db.execute(query,values)]
    def snapshot(self):
        with self.connection(readonly=True) as db:
            identities=[row[0] for row in db.execute('SELECT id FROM jobs ORDER BY created_utc,id')]
            if len(identities)>MAX_JOBS: raise TrackerError('Snapshot exceeds job limit')
            result={'schema':'outlands-job-quote-report/1','app_version':VERSION,
                    'interpretation':'Private local records. Approval references are operator-supplied records, not verified signatures or authority.',
                    'jobs':[self.detail(db,identity) for identity in identities]}
            if len(json_bytes(result))>MAX_EXPORT: raise TrackerError('Report snapshot exceeds 32 MiB')
            return result
    def backup(self,output,cancel=None):
        plain_path(self.path)
        if not self.path.is_file() or self.path.stat().st_size>MAX_STORE: raise TrackerError('Store file is unavailable or over its size limit')
        target=new_directory(output);check_cancel(cancel);target.mkdir(mode=0o700)
        dest=target/'store.sqlite';fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600);os.close(fd)
        source=snapshot=None
        started=time.monotonic()
        try:
            source=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=5,isolation_level=None)
            source.execute('PRAGMA trusted_schema=OFF');check_schema(source)
            snapshot=sqlite3.connect(dest,isolation_level=None)
            def progress(status,remaining,total):
                check_cancel(cancel)
                if time.monotonic()-started>10: raise TrackerError('Backup exceeded its cooperative ten-second budget')
            source.backup(snapshot,pages=64,progress=progress,sleep=.01)
            snapshot.execute('PRAGMA journal_mode=DELETE');check_schema(snapshot,True)
        except sqlite3.Error: raise TrackerError('SQLite backup failed; partial new output may remain') from None
        finally:
            if snapshot is not None:snapshot.close()
            if source is not None:source.close()
        data=dest.read_bytes()
        if len(data)>MAX_STORE: raise TrackerError('Backup exceeds 128 MiB')
        manifest={'schema':'outlands-job-quote-backup/1','store_schema_version':1,
                  'files':[{'path':'store.sqlite','bytes':len(data),'sha256':sha(data)}]}
        (target/'MANIFEST.json').write_bytes(json_bytes(manifest));verify_backup(target)
        return {'status':'PASS','backup_files':2,'store_sha256':sha(data)}

def new_directory(value):
    path=plain_path(value,False);plain_path(path.parent)
    if path.exists(): raise TrackerError('Choose a new output directory; existing output is never replaced')
    return path
def verify_backup(folder):
    folder=plain_path(folder)
    if not folder.is_dir() or {p.name for p in folder.iterdir()}!={'store.sqlite','MANIFEST.json'}:
        raise TrackerError('Backup must contain exactly store.sqlite and MANIFEST.json')
    path=plain_path(folder/'MANIFEST.json');source=plain_path(folder/'store.sqlite')
    try:
        if path.stat().st_size>4096 or source.stat().st_size>MAX_STORE: raise TrackerError('Backup exceeds its size bounds')
        manifest=json.loads(path.read_text(encoding='utf8'))
        if manifest.get('schema')!='outlands-job-quote-backup/1' or manifest.get('store_schema_version')!=1 or not isinstance(manifest.get('files'),list) or len(manifest['files'])!=1:
            raise TrackerError('Invalid backup manifest')
        record=manifest['files'][0]
        if record.get('path')!='store.sqlite' or type(record.get('bytes')) is not int or not isinstance(record.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',record['sha256']):
            raise TrackerError('Invalid backup record')
        data=source.read_bytes()
        if len(data)!=record['bytes'] or sha(data)!=record['sha256']: raise TrackerError('Backup bytes do not match the manifest')
        with Store(source).connection(readonly=True) as db:check_schema(db,True)
        return {'status':'PASS','bytes':len(data),'sha256':sha(data)}
    except (OSError,UnicodeError,json.JSONDecodeError,AttributeError,TypeError,RecursionError): raise TrackerError('Unreadable or malformed backup') from None
def restore_backup(folder,output):
    verify_backup(folder);source=plain_path(Path(folder)/'store.sqlite')
    target=plain_path(output,False);plain_path(target.parent)
    if target.suffix.lower()!='.sqlite': raise TrackerError('Restore target needs a new .sqlite filename')
    data=source.read_bytes()
    if sha(data)!=verify_backup(folder)['sha256']:raise TrackerError('Backup changed during recovery')
    try:
        with target.open('xb') as stream:stream.write(data)
    except OSError:raise TrackerError('Restore failed; existing files are never replaced and partial new output may remain') from None
    with Store(target).connection(readonly=True) as db:check_schema(db,True)
    return {'status':'PASS','restored_bytes':len(data),'sha256':sha(data)}

STYLE='''body{font:16px/1.6 system-ui,sans-serif;color:#183042;background:#eef3f6;margin:0}main{max-width:1100px;margin:30px auto;background:white;padding:32px;border-top:6px solid #08776e}h1,h2{line-height:1.2}h2{color:#08776e;margin-top:32px}table{border-collapse:collapse;width:100%}th,td{padding:10px;border:1px solid #dae2e6;text-align:left;vertical-align:top}p,td{white-space:pre-wrap;overflow-wrap:anywhere}.muted{color:#526373}section{border-bottom:1px solid #dae2e6;padding:12px 0}a{color:#075f80}@media(max-width:700px){main{margin:0;padding:18px}table{font-size:13px}}'''
def export_report(store,output,cancel=None):
    target=new_directory(output);check_cancel(cancel);data=store.snapshot()
    body='<h1>Job & Quote Tracker - private report</h1><p class="muted">Approval decisions and references are local operator records. This report is not an invoice, signature, permit check or proof of authority.</p>'
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['job_id','title','customer','contact','status','follow_up','scheduled_date','current_revision','amount','currency','decision'])
    def cell(value):
        value=str(value)
        return "'"+value if value.startswith(('=','+','-','@','\t','\r','\n')) else value
    for job in data['jobs']:
        check_cancel(cancel);q=job['quotes'][-1] if job['quotes'] else None;decision=q['decision']['decision'] if q and q['decision'] else ''
        writer.writerow([cell(x) for x in [job['id'],job['title'],job['customer'],job['contact'],job['status'],job['follow_up'],job['scheduled_date'],q['revision'] if q else '',q['amount'] if q else '',q['currency'] if q else '',decision]])
        esc=html.escape
        body+=f'<section><h2>{esc(job["title"])}</h2><p>{esc(job["id"])} | {esc(job["status"])} | version {job["version"]}</p><p><strong>Customer:</strong> {esc(job["customer"])}\n<strong>Contact:</strong> {esc(job["contact"])}\n<strong>Follow-up:</strong> {esc(job["follow_up"])}\n<strong>Scheduled:</strong> {esc(job["scheduled_date"])}</p><p>{esc(job["notes"])}</p>'
        if job['quotes']:
            body+='<h3>Quote revisions</h3>'
            for quote in job['quotes']:
                body+=f'<h4>Revision {quote["revision"]}: {quote["amount"]} {esc(quote["currency"])}</h4><p>{esc(quote["scope"])}</p><p><strong>Exclusions:</strong> {esc(quote["exclusions"])}</p>'
                if quote['decision']:body+=f'<p><strong>Recorded decision:</strong> {esc(quote["decision"]["decision"])}\n<strong>Reference:</strong> {esc(quote["decision"]["reference"])}</p>'
        body+='</section>'
    document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\';style-src \'unsafe-inline\';base-uri \'none\';form-action \'none\'"><title>Private job report</title><style>'+STYLE+'</style></head><body><main>'+body+'</main></body></html>'
    members={'index.html':document.encode('utf8'),'jobs.csv':stream.getvalue().encode('utf8'),'data.json':json_bytes(data),
             'README.txt':b'Private job/quote report. Includes customer, contact, notes, prices, references and activity. Do not publish by default. Not a backup; use verified SQLite backup/recovery.\n'}
    if sum(map(len,members.values()))>MAX_EXPORT:raise TrackerError('Report exceeds 32 MiB')
    members['MANIFEST.json']=json_bytes({'schema':'outlands-job-quote-report-files/1','files':[{'path':name,'bytes':len(content),'sha256':sha(content)} for name,content in sorted(members.items())]})
    check_cancel(cancel);target.mkdir(mode=0o700)
    try:
        for name,content in members.items():
            check_cancel(cancel)
            with (target/name).open('xb') as stream:stream.write(content)
            if sha((target/name).read_bytes())!=sha(content):raise TrackerError('Written report bytes differ')
    except OSError:raise TrackerError('Report write failed; partial new output may remain') from None
    return {'status':'PASS','files':5,'jobs':len(data['jobs'])}

def create_demo(path):
    store=Store.create(path)
    job=store.new_job({'title':'Fictional workshop shelf','customer':'Example Customer A','contact':'demo@example.invalid','notes':'Generated demonstration only. No real customer or job.','follow_up':'2026-11-15'})
    job=store.add_quote(job['id'],{'amount':'125.00','currency':'USD','scope':'Fictional shelf materials and assembly.','exclusions':'No installation or tax calculation.'},job['version'])
    store.decide(job['id'],'approved','Fictional acceptance record - not a real customer approval.',job['version'])
    store.new_job({'title':'Fictional garden sign','customer':'Example Customer B','follow_up':'2026-11-20','notes':'Draft request, not yet quoted.'})
    return store

def cli(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version=VERSION)
    subs=parser.add_subparsers(dest='command')
    for name in ['init','demo','gui','list','show','new','edit','quote','decision','status','backup','export']:
        part=subs.add_parser(name);part.add_argument('store')
        if name in ['show','edit','quote','decision','status']:part.add_argument('job')
        if name in ['new','edit','quote']:part.add_argument('--input',required=True)
        if name in ['edit','quote','decision','status']:part.add_argument('--expected-version',type=int,required=True)
        if name=='list':part.add_argument('--status',choices=STATES);part.add_argument('--due-before')
        if name=='decision':part.add_argument('--state',choices=['approved','rejected'],required=True);part.add_argument('--reference',required=True)
        if name=='status':part.add_argument('--state',choices=STATES,required=True);part.add_argument('--date',default='')
        if name in ['backup','export']:part.add_argument('output')
    verify=subs.add_parser('verify-backup');verify.add_argument('folder')
    restore=subs.add_parser('restore');restore.add_argument('folder');restore.add_argument('output')
    args=parser.parse_args(argv)
    try:
        if args.command in [None,'gui']:
            try:from tracker_gui import main
            except ImportError:raise TrackerError('Tk is unavailable; install your OS Tk package or use CLI commands') from None
            main(args.store if args.command else None);return 0
        if args.command in ['init','demo']:
            store=create_demo(args.store) if args.command=='demo' else Store.create(args.store)
            result={'status':'PASS','jobs':len(store.list_jobs())}
        elif args.command=='verify-backup':result=verify_backup(args.folder)
        elif args.command=='restore':result=restore_backup(args.folder,args.output)
        else:
            store=Store(args.store)
            if args.command=='list':result={'jobs':store.list_jobs(args.status,args.due_before)}
            elif args.command=='show':result=store.get(args.job)
            elif args.command=='new':result=store.new_job(read_json(args.input))
            elif args.command=='edit':result=store.edit_job(args.job,read_json(args.input),args.expected_version)
            elif args.command=='quote':result=store.add_quote(args.job,read_json(args.input),args.expected_version)
            elif args.command=='decision':result=store.decide(args.job,args.state,args.reference,args.expected_version)
            elif args.command=='status':result=store.set_status(args.job,args.state,args.expected_version,args.date)
            elif args.command=='backup':result=store.backup(args.output)
            elif args.command=='export':result=export_report(store,args.output)
        print(json.dumps(result,ensure_ascii=True));return 0
    except (TrackerError,OSError) as error:
        print(json.dumps({'status':'FAIL','code':str(error) if isinstance(error,TrackerError) else 'Filesystem operation failed; partial new output may remain'}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(cli())
