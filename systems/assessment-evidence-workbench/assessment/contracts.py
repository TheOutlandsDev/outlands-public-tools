"""Bounded declarations and deterministic manual review transitions."""
import base64
import copy
import re
from . import runtime as r
from .vendor import record_contract as legacy

STATES={'New','Triaged','Needs more info','Retesting','Resolved','Duplicate','Not applicable','Accepted risk'}
TRANSITIONS={
 'New':{'Triaged','Needs more info','Duplicate','Not applicable','Accepted risk'},
 'Triaged':{'Needs more info','Duplicate','Not applicable','Accepted risk'},
 'Needs more info':{'New','Triaged','Duplicate','Not applicable','Accepted risk'},
 'Retesting':{'Triaged','Needs more info','Duplicate','Not applicable','Accepted risk'},
 **{name:{'Triaged'} for name in ('Resolved','Duplicate','Not applicable','Accepted risk')}}
MAX_RECEIPT=49152
MAX_DOCUMENT=768*1024
MAX_REVISIONS=64

def fail(code):raise r.WorkbenchError(code)
def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):fail('FIELDS_INVALID')
def text(value,maximum=4000,empty=False):
    if type(value) is not str or (not empty and not value.strip()) or len(value)>maximum:fail('TEXT_INVALID')
    if any(ord(ch)<32 and ch not in '\n\r\t' for ch in value):fail('TEXT_CONTROL_REFUSED')
    try:raw=value.encode('utf-8')
    except UnicodeError:fail('TEXT_ENCODING_INVALID')
    if len(raw)>maximum:fail('TEXT_SIZE_LIMIT')
    return value
def token(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,39}',value):fail('IDENTIFIER_INVALID')
    if value in {'con','prn','aux','nul',*{prefix+str(i) for prefix in ('com','lpt') for i in range(1,10)}}:fail('IDENTIFIER_RESERVED')
    return value
def integer(value,low=1,high=1000000):
    if type(value) is not int or not low<=value<=high:fail('INTEGER_INVALID')
    return value
def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):fail('HASH_INVALID')
    return value
def choice(value,values):
    if type(value) is not str or value not in values:fail('CHOICE_INVALID')
    return value
def get(document,kind,identifier):
    token(identifier)
    for row in document[kind]:
        if row['id']==identifier:return row
    fail('RECORD_NOT_FOUND')
def unique(document,identifier):
    token(identifier)
    if any(row['id']==identifier for kind in ('submissions','findings','retests') for row in document[kind]):fail('DUPLICATE_RECORD_ID')
def receipt(value):
    text(value,65536)
    try:raw=base64.b64decode(value,validate=True)
    except (ValueError,TypeError):fail('RECEIPT_ENCODING_INVALID')
    if not 1<=len(raw)<=MAX_RECEIPT or base64.b64encode(raw).decode()!=value:fail('RECEIPT_SIZE_OR_ENCODING_INVALID')
    return dict(content_base64=value,bytes=len(raw),sha256=r.digest(raw))
def create(value):
    fields(value,('assessment_id','title','owner','scope','authorization_reference','handling_notes'))
    token(value['assessment_id'])
    for name in ('title','owner','scope','authorization_reference','handling_notes'):text(value[name],160 if name in ('title','owner') else 4000,empty=name=='handling_notes')
    return dict(format='outlands-assessment-management-v1',**copy.deepcopy(value),submissions=[],findings=[],retests=[],legacy_records=None)

def apply(document,command):
    fields(command,('operation','actor','reason','data'));text(command['actor'],160);text(command['reason']);data=command['data'];op=choice(command['operation'],('submission','finding','amend','transition','retest','review','legacy'));doc=copy.deepcopy(document)
    if op=='submission':
        fields(data,('id','series_id','revision','title','package_kind','receipt_base64'));unique(doc,data['id']);token(data['series_id']);integer(data['revision']);text(data['title'],160);choice(data['package_kind'],('source','build','installer','container','evidence'))
        if any(row['series_id']==data['series_id'] and row['revision']==data['revision'] for row in doc['submissions']):fail('DUPLICATE_SERIES_REVISION')
        item={k:v for k,v in data.items() if k!='receipt_base64'};item['receipt']=receipt(data['receipt_base64']);doc['submissions'].append(item)
    elif op=='finding':
        fields(data,('id','submission_id','title','severity','description','impact','reproduction','evidence_reference','remediation'));unique(doc,data['id']);submission=get(doc,'submissions',data['submission_id']);narrative(data)
        doc['findings'].append(dict(**data,submission_sha256=submission['receipt']['sha256'],state='New',revision=1,duplicate_of='',risk_owner='',review_condition=''))
    elif op=='amend':
        fields(data,('finding_id','expected_revision','title','severity','description','impact','reproduction','evidence_reference','remediation'));finding=get(doc,'findings',data['finding_id']);revision(finding,data);narrative(data)
        if finding['state'] not in ('New','Triaged','Needs more info'):fail('AMEND_REQUIRES_OPEN_FINDING')
        finding.update({k:v for k,v in data.items() if k not in ('finding_id','expected_revision')});finding['revision']+=1
    elif op=='transition':
        fields(data,('finding_id','expected_revision','state','duplicate_of','risk_owner','review_condition'));finding=get(doc,'findings',data['finding_id']);revision(finding,data);state=choice(data['state'],STATES)
        if state not in TRANSITIONS[finding['state']]:fail('TRANSITION_REFUSED')
        for name in ('duplicate_of','risk_owner','review_condition'):text(data[name],4000,empty=True)
        if state=='Duplicate':
            target=get(doc,'findings',data['duplicate_of'])
            if target['id']==finding['id'] or target['state']=='Duplicate' or any(row['duplicate_of']==finding['id'] for row in doc['findings']):fail('DUPLICATE_REFERENCE_REFUSED')
        elif data['duplicate_of']:fail('DUPLICATE_FIELDS_REFUSED')
        if state=='Accepted risk':text(data['risk_owner'],160);text(data['review_condition'])
        elif data['risk_owner'] or data['review_condition']:fail('RISK_FIELDS_REFUSED')
        finding.update({k:data[k] for k in ('state','duplicate_of','risk_owner','review_condition')});finding['revision']+=1
    elif op=='retest':
        fields(data,('id','finding_id','expected_revision','replacement_submission_id','outcome','reproduction_notes','positive_control_notes','evidence_reference','limitations'));unique(doc,data['id']);finding=get(doc,'findings',data['finding_id']);revision(finding,data)
        if finding['state'] not in ('Triaged','Retesting'):fail('RETEST_REQUIRES_TRIAGE')
        if any(row['finding_id']==finding['id'] and row['review_state']=='pending' and row['finding_revision']==finding['revision'] for row in doc['retests']):fail('RETEST_REVIEW_PENDING')
        original=get(doc,'submissions',finding['submission_id']);replacement=get(doc,'submissions',data['replacement_submission_id']);later(original,replacement)
        choice(data['outcome'],('Fixed','Not fixed','Inconclusive','Not performed'))
        for name in ('reproduction_notes','positive_control_notes','evidence_reference','limitations'):text(data[name],4000,empty=True)
        if data['outcome']=='Fixed':
            for name in ('reproduction_notes','positive_control_notes','evidence_reference'):text(data[name])
        elif not data['reproduction_notes'].strip() and not data['limitations'].strip():fail('RETEST_NOTES_REQUIRED')
        finding['state']='Retesting';finding['revision']+=1
        item={k:v for k,v in data.items() if k!='expected_revision'};item.update(original_submission_id=original['id'],original_sha256=original['receipt']['sha256'],replacement_sha256=replacement['receipt']['sha256'],finding_revision=finding['revision'],review_state='pending',reviewer='',review_reason='');doc['retests'].append(item)
    elif op=='review':
        fields(data,('retest_id','expected_revision','decision'));row=get(doc,'retests',data['retest_id']);finding=get(doc,'findings',row['finding_id']);revision(finding,data);choice(data['decision'],('accept','reject'))
        if row['review_state']!='pending' or finding['state']!='Retesting' or finding['revision']!=row['finding_revision']:fail('RETEST_REVIEW_STALE')
        replacement=get(doc,'submissions',row['replacement_submission_id'])
        if data['decision']=='accept' and row['outcome']=='Fixed' and any(s['series_id']==replacement['series_id'] and s['revision']>replacement['revision'] for s in doc['submissions']):fail('REPLACEMENT_NOT_LATEST')
        row.update(review_state=data['decision'],reviewer=command['actor'],review_reason=command['reason']);finding['state']='Resolved' if data['decision']=='accept' and row['outcome']=='Fixed' else 'Triaged';finding['revision']+=1
    else:
        fields(data,('records',))
        if doc['legacy_records'] is not None:fail('LEGACY_ALREADY_IMPORTED')
        if len(r.encode(data['records']))>legacy.MAX_INPUT_BYTES:fail('LEGACY_SIZE_LIMIT')
        try:parsed=legacy.parse_records(data['records'])
        except legacy.ContractError as error:fail(str(error))
        doc['legacy_records']=parsed
    if any(len(doc[kind])>32 for kind in ('submissions','findings','retests')):fail('RECORD_LIMIT')
    if sum(row['receipt']['bytes'] for row in doc['submissions'])>256*1024:fail('RECEIPT_TOTAL_LIMIT')
    if len(r.encode(doc))>MAX_DOCUMENT:fail('DOCUMENT_LIMIT')
    return doc

def narrative(data):
    text(data['title'],160);choice(data['severity'],('Informational','Low','Medium','High','Critical'))
    for name in ('description','impact','reproduction','evidence_reference','remediation'):text(data[name])
def revision(finding,data):
    integer(data['expected_revision'])
    if data['expected_revision']!=finding['revision']:fail('FINDING_REVISION_CONFLICT')
def later(original,replacement):
    if original['series_id']!=replacement['series_id'] or replacement['revision']<=original['revision']:fail('REPLACEMENT_NOT_LATER_IN_SERIES')
