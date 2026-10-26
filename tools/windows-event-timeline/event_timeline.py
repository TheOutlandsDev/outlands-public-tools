"""Build a timeline from selected saved Windows event metadata; no log queries. MIT."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import json
import re
import unicodedata
import uuid
from restricted_xml import parse as parse_xml
from inspection_support import (MAX_BYTES,Parser,TextError,bounded_append,cli_error,
                                finish,require,source_inputs,source_record,strict_json,
                                write_report)

NAMESPACE='http://schemas.microsoft.com/win/2004/08/events/event'
SCALE=10000000
STAMP=re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})\Z',re.ASCII)
REQUIRED={'provider','event_id','time_created'}
OPTIONAL={'provider_guid','channel','record_id','level','version','qualifiers','computer'}


def signal(report,code,source,position,coverage=False):
    rows=report['coverage_issues' if coverage else 'findings'];row={'code':code,'source':source,'record_index':position}
    if row not in rows:bounded_append(rows,row)


def timestamp(value):
    require(type(value) is str and len(value)<=40,'UNSUPPORTED_EVENT_TIMESTAMP')
    match=STAMP.fullmatch(value);require(match is not None,'UNSUPPORTED_EVENT_TIMESTAMP')
    zone=match[8];offset=0
    require(zone!='-00:00','UNSUPPORTED_EVENT_TIMESTAMP')
    if zone!='Z':
        hour=int(zone[1:3]);minute=int(zone[4:6])
        require(hour<=14 and minute<60 and (hour<14 or minute==0),'UNSUPPORTED_EVENT_TIMESTAMP')
        offset=(hour*60+minute)*(1 if zone[0]=='+' else -1)
    try:
        whole=datetime(*(int(match[i]) for i in range(1,7)),tzinfo=timezone(timedelta(minutes=offset))).astimezone(timezone.utc)
    except (ValueError,OverflowError):raise TextError('UNSUPPORTED_EVENT_TIMESTAMP') from None
    fraction=int((match[7] or '').ljust(7,'0'));delta=whole-datetime(1970,1,1,tzinfo=timezone.utc)
    ticks=(delta.days*86400+delta.seconds)*SCALE+fraction
    canonical=f'{whole.year:04d}-{whole.month:02d}-{whole.day:02d}T{whole.hour:02d}:{whole.minute:02d}:{whole.second:02d}.{fraction:07d}Z'
    return ticks,canonical


def short_text(value):
    return type(value) is str and 1<=len(value)<=256 and not any(unicodedata.category(c).startswith('C') for c in value)


def normalize(raw):
    require(type(raw) is dict and REQUIRED<=set(raw),'UNSUPPORTED_EVENT_RECORD')
    require(short_text(raw['provider']),'UNSUPPORTED_EVENT_RECORD')
    require(type(raw['event_id']) is int and 0<=raw['event_id']<=65535,'UNSUPPORTED_EVENT_RECORD')
    ticks,utc=timestamp(raw['time_created']);record={'provider':raw['provider'],'event_id':raw['event_id'],'ticks':ticks,'utc':utc}
    for field,maximum in [('record_id',2**64-1),('level',255),('version',255),('qualifiers',65535)]:
        value=raw.get(field);require(value is None or type(value) is int and 0<=value<=maximum,'UNSUPPORTED_EVENT_RECORD');record[field]=value
    for field in ('channel','computer'):
        value=raw.get(field);require(value is None or short_text(value),'UNSUPPORTED_EVENT_RECORD');record[field]=value
    guid=raw.get('provider_guid')
    require(guid is None or type(guid) is str and len(guid)<=64,'UNSUPPORTED_EVENT_RECORD')
    try:record['provider_guid']=str(uuid.UUID(guid)) if guid is not None else None
    except ValueError:raise TextError('UNSUPPORTED_EVENT_RECORD') from None
    return record


def json_records(data,source,report):
    value=strict_json(data,MAX_BYTES,40000,8192)
    require(type(value) is dict and set(value)=={'schema_version','events'} and type(value['schema_version']) is int
            and value['schema_version']==1 and type(value['events']) is list,'INVALID_EVENT_EXPORT_SCHEMA')
    require(len(value['events'])<=4000,'EVENT_COUNT_LIMIT')
    for index,event in enumerate(value['events'],1):
        if type(event) is dict and set(event)-(REQUIRED|OPTIONAL):signal(report,'UNINSPECTED_EVENT_FIELDS',source,index,True)
        yield index,event


def xml_records(data,source,report):
    root,_positions=parse_xml(data,lambda:signal(report,'XML_PROCESSING_INSTRUCTION_UNINSPECTED',source,0,True))
    def ns(node,inherited):return node.get('xmlns',inherited)
    root_ns=ns(root,'')
    if root.tag not in {'Events','Event'} or root_ns not in {'',NAMESPACE} or any(':' in key for key in root.attrib):
        signal(report,'UNSUPPORTED_EVENT_XML_ROOT',source,0,True);return
    if set(root.attrib)-{'xmlns'}:signal(report,'UNINSPECTED_XML_ATTRIBUTES',source,0,True)
    if root.tag=='Events' and (root.text.strip(' \t\n') or any(child.tail.strip(' \t\n') for child in root)):
        signal(report,'UNINSPECTED_XML_MIXED_TEXT',source,0,True)
    events=[root] if root.tag=='Event' else list(root)
    require(len(events)<=4000,'EVENT_COUNT_LIMIT')
    for index,event in enumerate(events,1):
        try:
            event_ns=ns(event,root_ns)
            require(event.tag=='Event' and event_ns in {'',NAMESPACE} and not any(':' in key for key in event.attrib),'UNSUPPORTED_EVENT_XML_RECORD')
            if set(event.attrib)-{'xmlns'}:signal(report,'UNINSPECTED_XML_ATTRIBUTES',source,index,True)
            systems=event.findall('System');require(len(systems)==1,'UNSUPPORTED_EVENT_XML_RECORD');system=systems[0]
            require(ns(system,event_ns)==event_ns and not any(':' in key for key in system.attrib),'UNSUPPORTED_EVENT_XML_RECORD')
            if set(system.attrib)-{'xmlns'}:signal(report,'UNINSPECTED_XML_ATTRIBUTES',source,index,True)
            def nodes(name,required=False):
                values=system.findall(name);require(len(values)==1 if required else len(values)<=1,'UNSUPPORTED_EVENT_XML_RECORD')
                for node in values:
                    require(ns(node,event_ns)==event_ns and not any(':' in key for key in node.attrib),'UNSUPPORTED_EVENT_XML_RECORD')
                return values
            def scalar(name):
                values=nodes(name)
                if not values:return None
                node=values[0];require(not len(node) and not (set(node.attrib)-{'xmlns'}),'UNSUPPORTED_EVENT_XML_RECORD')
                return node.text.strip(' \t\n')
            provider=nodes('Provider',True)[0];time=nodes('TimeCreated',True)[0];identity=nodes('EventID',True)[0]
            require(not len(provider) and not len(time) and not len(identity),'UNSUPPORTED_EVENT_XML_RECORD')
            if set(provider.attrib)-{'Name','Guid','xmlns'} or set(time.attrib)-{'SystemTime','xmlns'} or set(identity.attrib)-{'Qualifiers','xmlns'}:
                signal(report,'UNINSPECTED_XML_ATTRIBUTES',source,index,True)
            if provider.text.strip(' \t\n') or time.text.strip(' \t\n'):
                signal(report,'UNINSPECTED_XML_MIXED_TEXT',source,index,True)
            def number(value):
                if value is None:return None
                require(re.fullmatch(r'[0-9]{1,20}',value,re.ASCII) is not None,'UNSUPPORTED_EVENT_XML_RECORD');return int(value)
            raw={'provider':provider.get('Name'),'provider_guid':provider.get('Guid'),'event_id':number(identity.text.strip(' \t\n')),
                 'time_created':time.get('SystemTime'),'channel':scalar('Channel'),'record_id':number(scalar('EventRecordID')),
                 'level':number(scalar('Level')),'version':number(scalar('Version')),'qualifiers':number(identity.get('Qualifiers')),'computer':scalar('Computer')}
            known={'Provider','TimeCreated','EventID','Channel','EventRecordID','Level','Version','Computer','Security','Execution','Correlation','Keywords','Task','Opcode'}
            if any(child.tag not in known for child in system):signal(report,'UNINSPECTED_SYSTEM_FIELD',source,index,True)
            if any(child.tag not in {'System','EventData','UserData','DebugData','BinaryEventData','ProcessingErrorData','RenderingInfo'} for child in event):
                signal(report,'UNINSPECTED_EVENT_XML_FIELD',source,index,True)
            if system.text.strip(' \t\n') or any(child.tail.strip(' \t\n') for child in system) or event.text.strip(' \t\n') or any(child.tail.strip(' \t\n') for child in event):
                signal(report,'UNINSPECTED_XML_MIXED_TEXT',source,index,True)
            yield index,raw
        except TextError as error:signal(report,str(error),source,index,True)


def inspect(inputs,kind,gap_seconds=300,details=False):
    require(kind in {'json','xml'},'INPUT_FORMAT_UNSUPPORTED')
    require(type(gap_seconds) is int and 0<=gap_seconds<=31536000,'GAP_THRESHOLD_INVALID')
    report={'schema_version':1,'tool':'Windows Event Timeline Inspector','input_format':kind,'details_included':details,
            'scope':'Selected saved metadata only; declared clock times, source completeness and causation are unverified.',
            'gap_threshold_seconds':gap_seconds,'inputs':[],'timeline':[],'groups':[],'gaps':[],
            'findings':[],'coverage_issues':[],'computer_and_payload_fields_omitted':True}
    events=[];identities={};groups={}
    for source,data in inputs:
        report['inputs'].append(source_record(source,data))
        for index,raw in (json_records(data,source,report) if kind=='json' else xml_records(data,source,report)):
            try:record=normalize(raw)
            except TextError as error:signal(report,str(error),source,index,True);continue
            record.update(id=f'event-{len(events)+1:04d}',source=source,record_index=index)
            key=(record['provider'],record['provider_guid'],record['channel'],record['event_id'],record['version'],record['qualifiers'])
            if key not in groups:
                groups[key]={'id':f'group-{len(groups)+1:04d}','event_id':record['event_id'],'version':record['version'],
                             'qualifiers':record['qualifiers'],'count':0,'levels':[]}
                if details:groups[key].update(provider=record['provider'],provider_guid=record['provider_guid'],channel=record['channel'])
            group=groups[key];group['count']+=1
            if record['level'] not in group['levels']:group['levels'].append(record['level'])
            record['group_id']=group['id']
            if all(record[field] is not None for field in ('computer','channel','record_id')):
                identity=(source,record['computer'],record['channel'],record['record_id'])
                signature=tuple(record.get(field) for field in ('provider','provider_guid','event_id','version','qualifiers','ticks','level'))
                if identity in identities:signal(report,'DUPLICATE_EXPORTED_RECORD' if identities[identity]==signature else 'CONFLICTING_EXPORTED_RECORD_ID',source,index)
                else:identities[identity]=signature
            bounded_append(events,record)
    ordered=sorted(events,key=lambda row:row['ticks']);first=ordered[0]['ticks'] if ordered else 0
    previous=None
    for event in ordered:
        delta=event['ticks']-previous['ticks'] if previous else None
        row={key:event[key] for key in ('id','source','record_index','group_id','event_id','level')}
        # Decimal strings retain precision for consumers using IEEE-754 JSON numbers.
        row.update(elapsed_100ns=str(event['ticks']-first),delta_100ns=str(delta) if delta is not None else None)
        if details:row.update(time_created_utc=event['utc'],record_id=str(event['record_id']) if event['record_id'] is not None else None)
        bounded_append(report['timeline'],row)
        if gap_seconds and delta is not None and delta>gap_seconds*SCALE:
            bounded_append(report['gaps'],{'before_id':previous['id'],'after_id':event['id'],'duration_100ns':str(delta)})
            signal(report,'DECLARED_TIME_GAP_EXCEEDS_THRESHOLD',event['source'],event['record_index'])
        previous=event
    report['groups']=list(groups.values());report['input_order_was_chronological']=[r['id'] for r in events]==[r['id'] for r in ordered]
    report['repeated_groups']=sum(row['count']>1 for row in groups.values())
    report['duplicate_scope']='Within an individual selected source plus declared computer/channel/record ID only; unavailable identities and cross-file deduplication are not inferred.'
    return finish(report)


def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--file',action='append',required=True);parser.add_argument('--format',choices=('json','xml'),required=True)
    parser.add_argument('--gap-seconds',type=int,default=300);parser.add_argument('--output',required=True)
    parser.add_argument('--include-details',action='store_true')
    try:
        args=parser.parse_args(argv);report=inspect(source_inputs(args.file),args.format,args.gap_seconds,args.include_details)
        write_report(report,args.output,args.file)
        print(json.dumps({'status':report['status'],'events':len(report['timeline']),'groups':len(report['groups']),'gaps':len(report['gaps']),'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())
