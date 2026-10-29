"""Check explicit citation pins and exact quoted spans without truth claims."""
import toolkit as t
import knowledge_core as c


def answer(row):
    t.fields(row,{'id','text','citations'}); t.identifier(row['id']); c.text(row['text'])
    t.require(type(row['citations']) is list and len(row['citations'])<=100,'CITATION_LIMIT')
    citations=[]; seen=set()
    for entry in row['citations']:
        t.fields(entry,{'source','start','end','quote'})
        ref=c.reference(entry['source']); start=t.integer(entry['start'],4096)
        end=t.integer(entry['end'],4096,1); t.require(start<end,'SPAN_INVALID')
        quote=c.text(entry['quote']); key=(*c.ref_key(ref),start,end)
        t.require(key not in seen,'DUPLICATE_CITATION'); seen.add(key)
        citations.append(dict(source=ref,start=start,end=end,quote=quote))
    return row['id'],dict(id=row['id'],text=row['text'],citations=citations)


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','documents','answers'})
    t.require(value['format']=='outlands-answer-evidence-v1','FORMAT_INVALID')
    docs,dc,issues=c.documents(value['documents']); c.nonempty(docs,issues,'documents')
    answers,ac,other=c.rows(value['answers'],answer,'answers',100); issues+=other
    c.nonempty(answers,issues,'answers'); evidence=[]
    for key,(index,row) in sorted(answers.items()):
        def verify():
            t.require(row['citations'],'CITATIONS_MISSING'); checked=[]
            for citation in row['citations']:
                body=c.resolve(citation['source'],docs)['text']
                t.require(citation['end']<=len(body),'SPAN_OUT_OF_RANGE')
                quote=body[citation['start']:citation['end']]
                t.require(quote==citation['quote'],'QUOTE_MISMATCH')
                checked.append(dict(source=citation['source'],start=citation['start'],end=citation['end'],
                                    quote_sha256=t.digest(quote.encode('utf-8'))))
            return dict(id=key,answer_sha256=t.digest(row['text'].encode('utf-8')),
                        answer_characters=len(row['text']),checked_citations=checked)
        item=c.issue(issues,'answers',index,verify)
        if item is not None: evidence.append(item)
    result=c.base(raw,'outlands-answer-evidence-review-v1',dict(documents=dc,answers=ac),issues)
    result.update(evidence=evidence if not issues else None,offset_unit='UNICODE_CODE_POINT',end_boundary='EXCLUSIVE',
                  claim_support_verified=False,factual_truth_verified=False,answer_generated=False)
    return result


def main(argv=None): return c.cli('Check citation revisions, pins and exact source spans; no truth verification.',check,argv)
if __name__=='__main__': raise SystemExit(main())
