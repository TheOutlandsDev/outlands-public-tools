"""Recompute an explicit public intake preview and reconcile pinned receipt assertions."""
import struct
import zlib
import intake
import toolkit as t

COUNTS={'input_rows','accepted_records','duplicate_rows','rejected_rows','conflict_rows'}


def declaration(raw):
    value=t.decode(raw)
    t.fields(value,{'format','receipt_id','source_sha256','mapping_sha256','preview_sha256',
                    'source_format','sheet','counts'})
    t.require(value['format']=='outlands-ingestion-receipt-v1','RECEIPT_FORMAT_INVALID')
    t.identifier(value['receipt_id'])
    for field in ('source_sha256','mapping_sha256','preview_sha256'): t.sha(value[field])
    t.require(value['source_format'] in ('csv','xlsx'),'SOURCE_FORMAT_INVALID')
    t.require((value['source_format']=='csv' and value['sheet'] is None) or
              (value['source_format']=='xlsx' and type(value['sheet']) is str and
               0<len(value['sheet'])<=31),'SHEET_SELECTION_INVALID')
    t.fields(value['counts'],COUNTS)
    for count in value['counts'].values(): t.integer(count,1000)
    return value


def reconcile(receipt_raw,source_raw,mapping_raw,preview_raw):
    receipt=declaration(receipt_raw)
    for raw in (source_raw,mapping_raw,preview_raw):
        t.require(type(raw) is bytes and len(raw)<=t.MAX_INPUT,'INPUT_LIMIT')
    supplied=t.decode(preview_raw)
    try:
        observed=intake.preview(source_raw,mapping_raw,receipt['source_format'],receipt['sheet'])
    except (zlib.error,struct.error,EOFError):
        raise t.Rejected('INTAKE_REFUSED') from None
    issues=[]
    for field,raw in (('source_sha256',source_raw),('mapping_sha256',mapping_raw),('preview_sha256',preview_raw)):
        if receipt[field]!=t.digest(raw): issues.append(field.upper()+'_MISMATCH')
    # Compare canonical typed JSON, not Python equality (True must not equal 1).
    if t.encode(supplied)!=t.encode(observed): issues.append('PREVIEW_CONTENT_MISMATCH')
    counts=receipt['counts']
    if counts['input_rows']!=sum(counts[k] for k in COUNTS-{'input_rows'}):
        issues.append('DECLARED_ACCOUNTING_MISMATCH')
    if counts!=observed['counts']: issues.append('RECEIPT_COUNT_MISMATCH')
    if observed['status']!='PASS': issues.append('INTAKE_REQUIRES_REVIEW')
    ready=not issues
    return dict(status='PASS' if ready else 'REVIEW_REQUIRED',format='outlands-ingestion-reconciliation-v1',
                receipt_id=receipt['receipt_id'],receipt_sha256=t.digest(receipt_raw),
                source_sha256=t.digest(source_raw),mapping_sha256=t.digest(mapping_raw),
                supplied_preview_sha256=t.digest(preview_raw),
                recomputed_preview_sha256=t.digest(t.encode(observed)),observed_counts=observed['counts'],
                intake_status=observed['status'],issues=sorted(issues),
                row_counts_recomputed=True,ready_for_explicit_review=ready,
                source_authority_verified=False,imported=False,target_changes_performed=False)


def main(argv=None):
    p=t.Parser(description='Recompute public CSV/XLSX intake and compare an explicit pinned receipt.')
    for flag in ('receipt','source','mapping','preview'): p.add_argument('--'+flag,required=True)
    p.add_argument('--out')
    return t.run(p,lambda a:reconcile(t.read(a.receipt),t.read(a.source),t.read(a.mapping),t.read(a.preview)),argv)


if __name__=='__main__': raise SystemExit(main())
