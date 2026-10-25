"""Index and compare a bounded selected VINTF HAL-declaration subset. MIT."""
from __future__ import annotations
import json
import re
from restricted_xml import parse
from inspection_support import (Parser, TextError, bounded_append, cli_error, finish,
                                require, source_inputs, source_record,
                                write_report)

PACKAGE=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\Z')
INTERFACE=re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,127}\Z')
INSTANCE=re.compile(r'[A-Za-z0-9_][A-Za-z0-9_./-]{0,127}\Z')
HIDL_VERSION=re.compile(r'(?:0|[1-9][0-9]?)\.(?:0|[1-9][0-9]?)\Z')
AIDL_VERSION=re.compile(r'[1-9][0-9]{0,3}\Z')


def signal(report,code,source,element,coverage=False):
    rows=report['coverage_issues' if coverage else 'findings']
    row={'code':code,'source':source,'element':element}
    if row not in rows: bounded_append(rows,row)


def xml_tree(data,source,report):
    return parse(data,lambda:signal(report,'PROCESSING_INSTRUCTION_UNINSPECTED',source,0,True))


def extract(data,source,side,report,details):
    root,positions=xml_tree(data,source,report)
    def warn(code,node,coverage=True): signal(report,code,source,positions[id(node)],coverage)
    def scalar(node):
        if node.attrib or len(node): warn('UNSUPPORTED_SCALAR_STRUCTURE',node); return None
        return (node.text or '').strip(' \t\n')
    def one(parent,tag):
        children=parent.findall(tag)
        if len(children)!=1: warn('MISSING_OR_REPEATED_SCALAR',parent); return None
        return scalar(children[0])
    def mixed(parent):
        if (parent.text or '').strip(' \t\n') or any((child.tail or '').strip(' \t\n') for child in parent):
            warn('UNINSPECTED_MIXED_TEXT',parent)
    if any(':' in node.tag or any(':' in key or key=='xmlns' for key in node.attrib) for node in root.iter()):
        warn('UNSUPPORTED_XML_NAMESPACE',root);return []
    if root.tag!='manifest': warn('UNSUPPORTED_XML_ROOT',root); return []
    if root.get('version') not in {'1.0','2.0'} or root.get('type') not in {'device','framework'}:
        warn('UNSUPPORTED_MANIFEST_METADATA',root); return []
    if set(root.attrib)-{'version','type','target-level'}: warn('UNINSPECTED_MANIFEST_ATTRIBUTES',root)
    mixed(root)
    kind=root.get('type'); entries=[]
    for hal in root:
        if hal.tag!='hal': warn('UNINSPECTED_MANIFEST_ELEMENT',hal); continue
        report['hal_elements_observed']+=1
        mixed(hal)
        if set(hal.attrib)-{'format'}: warn('HAL_MODIFIERS_NOT_EVALUATED',hal)
        for child in hal:
            if child.tag not in {'name','version','transport','interface','fqname'}: warn('UNINSPECTED_HAL_ELEMENT',child)
        fmt=hal.get('format','hidl')
        if fmt not in {'hidl','aidl'}: warn('HAL_FORMAT_UNSUPPORTED',hal); continue
        if fmt=='aidl' and root.get('version')!='2.0': warn('AIDL_REQUIRES_SUPPORTED_META_VERSION',hal); continue
        name=one(hal,'name')
        if name is None or len(name)>256 or not PACKAGE.fullmatch(name): warn('UNSUPPORTED_PACKAGE_NAME',hal); continue
        versions=[]
        for child in hal.findall('version'):
            version=scalar(child); pattern=HIDL_VERSION if fmt=='hidl' else AIDL_VERSION
            if version is None or not pattern.fullmatch(version): warn('UNSUPPORTED_HAL_VERSION',child)
            else: versions.append(version)
        if len(set(versions))!=len(versions): warn('REPEATED_VERSION_DECLARATION',hal,False)
        if fmt=='aidl' and len(versions)!=1: warn('EXPLICIT_SINGLE_AIDL_VERSION_REQUIRED',hal); versions=[]
        if fmt=='hidl':
            majors=[v.split('.')[0] for v in versions]
            if len(set(majors))!=len(majors): warn('MULTIPLE_HIDL_VERSIONS_SAME_MAJOR',hal,False)
        transport=None; arch=None; transports=hal.findall('transport')
        if fmt=='hidl':
            if len(transports)!=1: warn('HIDL_TRANSPORT_NEEDS_REVIEW',hal)
            else:
                node=transports[0]; transport=(node.text or '').strip(' \t\n'); arch=node.get('arch')
                if len(node) or set(node.attrib)-{'arch'} or transport not in {'hwbinder','passthrough'}:
                    warn('HIDL_TRANSPORT_NEEDS_REVIEW',node)
                    transport=None;arch=None
                if (transport=='hwbinder' and arch is not None) or (transport=='passthrough' and arch not in {'32','64','32+64'}):
                    warn('HIDL_ARCH_NEEDS_REVIEW',node)
                    arch=None
        elif transports: warn('AIDL_TRANSPORT_UNINSPECTED',hal)
        candidates=[]
        for interface in hal.findall('interface'):
            mixed(interface)
            if interface.attrib: warn('UNINSPECTED_INTERFACE_ATTRIBUTES',interface)
            for child in interface:
                if child.tag not in {'name','instance'}: warn('UNINSPECTED_INTERFACE_ELEMENT',child)
            interface_name=one(interface,'name')
            if interface_name is None or not INTERFACE.fullmatch(interface_name): warn('UNSUPPORTED_INTERFACE_NAME',interface); continue
            instances=interface.findall('instance')
            if not versions or not instances: warn('INTERFACE_WITHOUT_EXPLICIT_VERSION_OR_INSTANCE',interface)
            for child in instances:
                instance=scalar(child)
                if instance is None or not INSTANCE.fullmatch(instance): warn('UNSUPPORTED_INSTANCE_NAME',child); continue
                for version in versions: bounded_append(candidates,(version,interface_name,instance,child))
        for child in hal.findall('fqname'):
            value=scalar(child)
            if value is None: continue
            if fmt=='hidl':
                match=re.fullmatch(r'@([^:]+)::([^/]+)/(.+)',value)
                if not match or not HIDL_VERSION.fullmatch(match[1]): warn('UNSUPPORTED_FQNAME',child); continue
                fq_versions=[match[1]]; interface_name=match[2]; instance=match[3]
            else:
                match=re.fullmatch(r'([^/]+)/(.+)',value)
                if not match: warn('UNSUPPORTED_FQNAME',child); continue
                fq_versions=versions; interface_name=match[1]; instance=match[2]
            if not INTERFACE.fullmatch(interface_name) or not INSTANCE.fullmatch(instance): warn('UNSUPPORTED_FQNAME',child); continue
            for version in fq_versions: bounded_append(candidates,(version,interface_name,instance,child))
        if not candidates: warn('HAL_WITHOUT_SUPPORTED_INSTANCE_DECLARATION',hal)
        for version,interface_name,instance,node in candidates:
            key=(kind,fmt,name,version,interface_name,instance)
            row={'id':f'declaration-{len(report["declarations"])+1:04d}','source':source,'side':side,'element':positions[id(node)],'format':fmt,'manifest_type':kind}
            fields={'package':name,'version':version,'interface':interface_name,'instance':instance,'transport':transport,'arch':arch}
            if details: row['fields']=fields
            bounded_append(report['declarations'],row); bounded_append(entries,(key,fields,row))
    return entries


def inspect(current,before=None,details=False):
    require(1<=len(current)<=32 and (before is None or 1<=len(before)<=32)
            and len(current)+(len(before) if before is not None else 0)<=32,'INPUT_COUNT_LIMIT')
    report={'schema_version':1,'tool':'Android VINTF Manifest Inspector',
            'scope':'Literal supported HAL instances in selected XML; no effective manifest merge or compatibility evaluation.',
            'details_included':details,'comparison_requested':before is not None,'inputs':[],
            'hal_elements_observed':0,'declarations':[],'changes':[],'ambiguous_comparisons':[],
            'findings':[],'coverage_issues':[]}
    groups=[]
    for side,inputs in [('before',before),('current',current)]:
        index={}
        for number,(_label,data) in enumerate(inputs or [],1):
            source=f'{side}-{number:04d}'; report['inputs'].append(source_record(source,data))
            for key,fields,row in extract(data,source,side,report,details): index.setdefault(key,[]).append((fields,row))
        for rows in index.values():
            if len(rows)>1:
                code='REPEATED_SELECTED_DECLARATION' if all(fields==rows[0][0] for fields,_row in rows) else 'CONFLICTING_SELECTED_DECLARATION'
                for _fields,row in rows: signal(report,code,row['source'],row['element'])
        groups.append(index)
    previous,now=groups
    if before is not None:
        for key in dict.fromkeys([*previous,*now]):
            left=previous.get(key,[]);right=now.get(key,[])
            if len(left)>1 or len(right)>1:
                bounded_append(report['ambiguous_comparisons'],{'before_ids':[r['id'] for _f,r in left],'current_ids':[r['id'] for _f,r in right]});continue
            changed=[] if not left or not right else [f for f in ('transport','arch') if left[0][0][f]!=right[0][0][f]]
            kind='added' if not left else 'removed' if not right else 'changed'
            if kind!='changed' or changed:
                bounded_append(report['changes'],{'kind':kind,'before_id':left[0][1]['id'] if left else None,'current_id':right[0][1]['id'] if right else None,'fields_changed':changed})
        if report['changes']: signal(report,'SELECTED_HAL_DECLARATIONS_CHANGED','comparison',0)
    report['comparison_scope']='Identity includes manifest type, format, package, version, interface and instance. Version changes are removal/addition. Duplicates are never arbitrarily paired.'
    return finish(report)


def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--file',action='append',required=True);parser.add_argument('--before',action='append')
    parser.add_argument('--output',required=True);parser.add_argument('--include-details',action='store_true')
    try:
        args=parser.parse_args(argv); paths=[*(args.before or []),*args.file]; inputs=source_inputs(paths)
        previous=inputs[:len(args.before)] if args.before else None; current=inputs[len(args.before or []):]
        report=inspect(current,previous,args.include_details);write_report(report,args.output,paths)
        print(json.dumps({'status':report['status'],'declarations':len(report['declarations']),'changes':len(report['changes']),'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())
