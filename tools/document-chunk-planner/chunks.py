"""Plan fixed character windows with exact source/chunk pins; no text extraction."""
import toolkit as t
import knowledge_core as c


def plan(raw):
    value=t.decode(raw); t.fields(value,{'format','documents','policy'})
    t.require(value['format']=='outlands-document-chunks-v1','FORMAT_INVALID')
    policy=value['policy']; t.fields(policy,{'max_chars','overlap_chars'})
    width=t.integer(policy['max_chars'],4096,1)
    overlap=t.integer(policy['overlap_chars'],width-1)
    docs,dc,issues=c.documents(value['documents']); c.nonempty(docs,issues,'documents')
    # Check count before allocating output windows; never truncate a plan.
    count=sum(1+max(0,(len(row['text'])-width+width-overlap-1)//(width-overlap)) for _,row in docs.values())
    if count>4096: issues.append(dict(side='documents',row=0,code='CHUNK_LIMIT'))
    chunks=None
    if not issues:
        chunks=[]
        for key in sorted(docs):
            row=docs[key][1]; start=0; index=0; body=row['text']
            while start<len(body):
                end=min(start+width,len(body)); part=body[start:end]; index+=1
                chunks.append(dict(id=key,revision=row['revision'],source_sha256=row['sha256'],index=index,
                                   start=start,end=end,characters=end-start,utf8_bytes=len(part.encode('utf-8')),
                                   sha256=t.digest(part.encode('utf-8'))))
                if end==len(body): break
                start=end-overlap
        t.require(len(chunks)==count,'CHUNK_ACCOUNTING_FAILED')
    result=c.base(raw,'outlands-document-chunk-plan-v1',dict(documents=dc),issues)
    result.update(policy=policy,policy_sha256=t.digest(t.encode(policy)),chunks=chunks,
                  chunk_count=len(chunks) if chunks is not None else None,
                  offset_unit='UNICODE_CODE_POINT',end_boundary='EXCLUSIVE',text_emitted=False,
                  token_budget_verified=False,target_updates_plan_only=True)
    return result


def main(argv=None): return c.cli('Plan pinned fixed character windows without emitting document text.',plan,argv)
if __name__=='__main__': raise SystemExit(main())
