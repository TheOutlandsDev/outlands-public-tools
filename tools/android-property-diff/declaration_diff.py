"""Original MIT selected-declaration comparison shared by standalone diff tools."""
from __future__ import annotations
import json
from inspection_support import (Parser, TextError, bounded_append, cli_error, finish,
                                issue, source_inputs, source_record, write_report)


def base_report(title,scope,details):
    return {'schema_version':1,'tool':title,'scope':scope,'details_included':details,
            'inputs':[],'records':[],'changes':[],'held_identities':[],'unidentified_rows':[],
            'findings':[],'coverage_issues':[]}


def unidentified(report,side,source,line):
    bounded_append(report['unidentified_rows'],{'side':side,'source':source,'line':line})


def register(report,index,side,source,line,key,fields):
    row={'id':f'record-{len(report["records"])+1:04d}','side':side,'source':source,'line':line,'supported':fields is not None}
    if report['details_included']:
        row['declared_identity']=key
        if fields is not None:row['fields']=fields
    bounded_append(report['records'],row);index.setdefault(key,[]).append((fields,row))


def compare(report,before,after):
    unchanged=0;compared=0
    uncertain={row['side'] for row in report['unidentified_rows']}
    for key in dict.fromkeys([*before,*after]):
        left=before.get(key,[]);right=after.get(key,[])
        duplicate=len(left)>1 or len(right)>1
        unsupported=any(fields is None for fields,_row in [*left,*right])
        unmatched_uncertain=(not left and 'before' in uncertain) or (not right and 'after' in uncertain)
        if duplicate or unsupported or unmatched_uncertain:
            held={'reason':'duplicate_declarations' if duplicate else 'unsupported_declaration' if unsupported else 'uninspected_identity_on_opposite_side',
                  'before_ids':[r['id'] for _f,r in left],'after_ids':[r['id'] for _f,r in right]}
            bounded_append(report['held_identities'],held)
            if duplicate:
                for _fields,row in [*left,*right]:issue(report['findings'],'AMBIGUOUS_DUPLICATE_DECLARATION',row['source'],row['line'])
            continue
        compared+=1
        kind='added' if not left else 'removed' if not right else 'changed'
        changed=list(right[0][0]) if not left else list(left[0][0]) if not right else [f for f in left[0][0] if left[0][0][f]!=right[0][0][f]]
        if kind=='changed' and not changed:unchanged+=1;continue
        bounded_append(report['changes'],{'kind':kind,'before_id':left[0][1]['id'] if left else None,
                                         'after_id':right[0][1]['id'] if right else None,'fields_changed':changed})
    report['comparison_counts']={'unique_compared':compared,'unchanged':unchanged,'held':len(report['held_identities'])}
    report['comparison_scope']='Unique parsed selected declarations only; unmatched identities are held when the opposite side has unidentified rows. No effective runtime state is inferred.'
    if report['changes']:issue(report['findings'],'SELECTED_DECLARATIONS_CHANGED','comparison',0)
    return finish(report)


def inspect_sets(before,after,title,scope,parse,details=False):
    report=base_report(title,scope,details);indexes=[]
    for side,inputs in [('before',before),('after',after)]:
        index={}
        for number,(_label,data) in enumerate(inputs,1):
            source=f'{side}-{number:04d}';report['inputs'].append(source_record(source,data))
            parse(data,side,source,report,index)
        indexes.append(index)
    return compare(report,*indexes)


def cli(inspector,description,argv=None):
    parser=Parser(description=description)
    parser.add_argument('--before',action='append',required=True)
    parser.add_argument('--after',action='append',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--include-details',action='store_true')
    try:
        args=parser.parse_args(argv);paths=[*args.before,*args.after];inputs=source_inputs(paths)
        report=inspector(inputs[:len(args.before)],inputs[len(args.before):],args.include_details)
        write_report(report,args.output,paths)
        print(json.dumps({'status':report['status'],'changes':len(report['changes']),
                          'held_identities':len(report['held_identities']),'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error:return cli_error(error)
