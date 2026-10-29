"""Bounded explicit documents, exact revisions, row accounting and fixed diagnostics."""
from collections import defaultdict
from fractions import Fraction
import toolkit as t


def rows(value,parser,side,maximum=1000):
    t.require(type(value) is list and len(value)<=maximum,'ROW_LIMIT')
    groups=defaultdict(list); issues=[]; rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row)
            groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1; issues.append(dict(side=side,row=index,code=str(error)))
    accepted={}; duplicate=conflict=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})!=1:
            conflict+=len(entries)
            issues.extend(dict(side=side,row=index,code='IDENTITY_CONFLICT') for index,_ in entries)
        else:
            accepted[key]=entries[0]; duplicate+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicate,
                conflict_rows=conflict,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicate+conflict+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues


def text(value):
    t.require(type(value) is str and 1<=len(value)<=4096,'TEXT_INVALID')
    # No Unicode or newline normalization: pins and offsets bind exact supplied text.
    t.require(all(ord(c)>=32 or c in '\n\r\t' for c in value),'TEXT_CONTROL_INVALID')
    t.require(not any(0x7f<=ord(c)<=0x9f for c in value),'TEXT_CONTROL_INVALID')
    return value


def reference(value):
    t.fields(value,{'id','revision','sha256'})
    t.identifier(value['id']); t.integer(value['revision'],1000000,1); t.sha(value['sha256'])
    return dict(value)


def document(value):
    t.fields(value,{'id','revision','sha256','text'})
    ref=reference({k:value[k] for k in ('id','revision','sha256')})
    body=text(value['text'])
    t.require(t.digest(body.encode('utf-8'))==ref['sha256'],'DOCUMENT_PIN_MISMATCH')
    return ref['id'],dict(**ref,text=body)


def documents(value):
    return rows(value,document,'documents',100)


def ref_key(ref): return (ref['id'],ref['revision'],ref['sha256'])


def resolve(ref,docs):
    item=docs.get(ref['id'])
    t.require(item is not None,'REFERENCE_MISSING')
    body=item[1]
    t.require(ref['revision']==body['revision'],'REFERENCE_REVISION_MISMATCH')
    t.require(ref['sha256']==body['sha256'],'REFERENCE_PIN_MISMATCH')
    return body


def references(value,maximum=100):
    t.require(type(value) is list and len(value)<=maximum,'REFERENCE_LIMIT')
    refs=[reference(v) for v in value]
    # Same document twice, even with changed pins, is ambiguous inside one list.
    t.require(len({r['id'] for r in refs})==len(refs),'DUPLICATE_REFERENCE')
    return refs


def ratio(value):
    value=Fraction(value)
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),
                counts=counts,issues=sorted(issues,key=lambda r:(r['side'],r['row'],r['code'])),
                source_authority_verified=False,content_privacy_verified=False,
                target_changes_performed=False)


def issue(issues,side,index,operation):
    try: return operation()
    except t.Rejected as error:
        issues.append(dict(side=side,row=index,code=str(error)))
        return None


def nonempty(accepted,issues,side):
    if not accepted: issues.append(dict(side=side,row=0,code='EMPTY_ACCEPTED_COHORT'))


def cli(description,operation,argv=None):
    parser=t.Parser(description=description)
    parser.add_argument('--input',required=True); parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
