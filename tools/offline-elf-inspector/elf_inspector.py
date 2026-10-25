"""Original MIT offline ELF metadata inspector with optional text hints; stdlib only."""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time

VERSION='1.1.0'
MAX_FILE=256*1024*1024
MAX_METADATA=64*1024*1024
MAX_HASH=512*1024*1024
MAX_REPORT=16*1024*1024
MAX_STRTAB=4*1024*1024
MAX_ELFS=1000
MAX_REFERENCES=10000
MAX_ISSUES=500
MAX_CANDIDATES=16
MAX_HINT_FILE_BYTES=8*1024*1024
MAX_HINT_TOTAL_BYTES=64*1024*1024
MAX_HINT_STRING=1024
MAX_HINTS_PER_FILE=128
MAX_HINTS_TOTAL=2000
HINT_CHUNK=64*1024
ASCII_RUNS=re.compile(rb'[\x20-\x7e]+|[^\x20-\x7e]+')
LIBRARY_HINT=re.compile(rb'(?<![A-Za-z0-9_./+\-])[A-Za-z0-9_./+\-]+\.so(?:\.[0-9]+)*(?![A-Za-z0-9_./+\-])')
CONFIG_HINT=re.compile(rb'(?<![A-Za-z0-9_./+\-])/(?:vendor/etc|odm/etc|system/etc|vendor/firmware|odm/firmware)/[A-Za-z0-9_./+\-]+')
MACHINES={3:'x86',8:'MIPS',20:'PowerPC',21:'PowerPC64',40:'ARM',62:'x86-64',183:'AArch64',243:'RISC-V'}

class InspectorError(ValueError):
    """Controlled failure containing a public code, never an input path or native error."""
class ParseError(InspectorError):pass
class ScanLimit(InspectorError):pass

@dataclass(frozen=True)
class Limits:
    max_files:int=2000
    max_entries:int=20000
    max_depth:int=32
    seconds:int=60
    def validate(self):
        for value,maximum in [(self.max_files,10000),(self.max_entries,100000),(self.max_depth,64),(self.seconds,300)]:
            if type(value) is not int or not 1<=value<=maximum:raise InspectorError('INVALID_SCAN_LIMIT')

def ordinary(value,existing=True):
    path=Path(os.path.abspath(value))
    if str(path).startswith('\\\\'):raise InspectorError('UNC_PATH_UNSUPPORTED')
    for part in [*reversed(path.parents),path]:
        try:info=part.lstat()
        except FileNotFoundError:
            if existing:raise InspectorError('INPUT_OR_PARENT_NOT_FOUND') from None
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise InspectorError('LINK_OR_REPARSE_PATH_UNSUPPORTED')
    return path

def supported_text(value):
    return isinstance(value,str) and len(value)<=1024 and not any(ord(c)<32 or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in value)

def identity(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
def stamp(info):return (*identity(info),info.st_ctime_ns)
def path_key(path):return os.path.normcase(str(path))
def digest(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=True,indent=2,sort_keys=True)+'\n').encode('utf8')

class Budget:
    def __init__(self,limits):
        limits.validate();self.limits=limits;self.start=time.monotonic()
        self.entries=0;self.files=0;self.metadata_bytes=0;self.hash_bytes=0;self.references=0
        self.hint_bytes=0;self.hint_count=0
    def check(self):
        if time.monotonic()-self.start>self.limits.seconds:raise ScanLimit('TIME_BUDGET_REACHED')
    def read(self,count,hashing=False):
        self.check()
        if hashing:
            if self.hash_bytes+count>MAX_HASH:raise ScanLimit('HASH_BYTE_BUDGET_REACHED')
            self.hash_bytes+=count
        else:
            if self.metadata_bytes+count>MAX_METADATA:raise ScanLimit('METADATA_BYTE_BUDGET_REACHED')
            self.metadata_bytes+=count

class Reader:
    def __init__(self,stream,size,budget):self.stream=stream;self.size=size;self.budget=budget
    def read(self,offset,length):
        if offset<0 or length<0 or offset>self.size or length>self.size-offset:raise ParseError('ELF_RANGE_OUTSIDE_FILE')
        self.budget.read(length);self.stream.seek(offset);data=self.stream.read(length)
        if len(data)!=length:raise ParseError('ELF_TRUNCATED_DURING_READ')
        return data

def scan_runtime_hints(stream,size,budget):
    """Observe bounded ASCII tokens; these guesses never enter dependency resolution."""
    maximum=min(size,MAX_HINT_FILE_BYTES,max(0,MAX_HINT_TOTAL_BYTES-budget.hint_bytes))
    reasons=set();observations={};long_runs=0;run=bytearray();run_start=0;overlong=False
    if maximum<size:
        if maximum==MAX_HINT_FILE_BYTES:reasons.add('PER_FILE_BYTE_LIMIT')
        if maximum==max(0,MAX_HINT_TOTAL_BYTES-budget.hint_bytes):reasons.add('GLOBAL_BYTE_LIMIT')
    def finish():
        nonlocal long_runs
        if overlong:
            long_runs+=1;reasons.add('STRING_LENGTH_LIMIT');return
        raw=bytes(run)
        for kind,pattern in [('library_text',LIBRARY_HINT),('config_or_firmware_path_text',CONFIG_HINT)]:
            for match in pattern.finditer(raw):
                value=match.group().decode('ascii');key=(kind,value)
                if key in observations:observations[key]['occurrences']+=1;continue
                if len(observations)>=MAX_HINTS_PER_FILE:reasons.add('FILE_HINT_COUNT_LIMIT');continue
                if budget.hint_count>=MAX_HINTS_TOTAL:reasons.add('GLOBAL_HINT_COUNT_LIMIT');continue
                observations[key]={'kind':kind,'text':value,'first_offset':run_start+match.start(),'occurrences':1}
                budget.hint_count+=1
    stream.seek(0);offset=0
    while offset<maximum:
        budget.check();count=min(HINT_CHUNK,maximum-offset);data=stream.read(count)
        if len(data)!=count:raise InspectorError('FILE_CHANGED_DURING_HINT_SCAN')
        budget.hint_bytes+=count
        for segment in ASCII_RUNS.finditer(data):
            part=segment.group()
            if 32<=part[0]<=126:
                if not run and not overlong:run_start=offset+segment.start()
                if not overlong:
                    if len(run)+len(part)>MAX_HINT_STRING:run.clear();overlong=True
                    else:run.extend(part)
            elif run or overlong:
                finish();run.clear();overlong=False
        offset+=count
    # A byte-limit cut can split a token: omit that final partial run entirely.
    if maximum==size and (run or overlong):finish()
    return {'coverage':'partial_ascii_scan' if reasons else 'complete_ascii_scan',
            'bytes_scanned':maximum,'file_bytes':size,'reasons':sorted(reasons),
            'overlong_ascii_runs_omitted':long_runs,
            'observations':sorted(observations.values(),key=lambda item:(item['kind'],item['text']))}

def parse_stream(stream,size,budget):
    """Parse supported metadata from file-backed program segments, never section names."""
    reader=Reader(stream,size,budget)
    if reader.read(0,min(4,size))!=b'\x7fELF':return None
    if size>MAX_FILE:raise ParseError('ELF_FILE_SIZE_LIMIT')
    ident=reader.read(0,16)
    if ident[4] not in (1,2) or ident[5] not in (1,2) or ident[6]!=1:raise ParseError('ELF_CLASS_ENDIAN_OR_VERSION_UNSUPPORTED')
    bits=32 if ident[4]==1 else 64;endian='little' if ident[5]==1 else 'big';order='<' if ident[5]==1 else '>'
    header_format=order+('HHIIIIIHHHHHH' if bits==32 else 'HHIQQQIHHHHHH')
    expected_header=52 if bits==32 else 64;expected_ph=32 if bits==32 else 56
    header=struct.unpack(header_format,reader.read(16,expected_header-16))
    kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phcount,shsize,shcount,shnames=header
    if kind not in (2,3):raise ParseError('ELF_TYPE_UNSUPPORTED_USE_EXEC_OR_DYN')
    if version!=1 or ehsize!=expected_header:raise ParseError('ELF_HEADER_SIZE_OR_VERSION_UNSUPPORTED')
    if phcount==0 or phcount==65535:raise ParseError('ELF_PROGRAM_HEADER_COUNT_UNSUPPORTED')
    if phcount>256 or phsize!=expected_ph or phoff<expected_header:raise ParseError('ELF_PROGRAM_HEADER_LAYOUT_UNSUPPORTED')
    table=reader.read(phoff,phsize*phcount);loads=[];dynamics=[];interpreters=[]
    for i in range(phcount):
        values=struct.unpack_from(order+('IIIIIIII' if bits==32 else 'IIQQQQQQ'),table,i*phsize)
        if bits==32:ptype,offset,address,physical,filesz,memsz,pflags,align=values
        else:ptype,pflags,offset,address,physical,filesz,memsz,align=values
        if ptype==0:continue # PT_NULL's other fields are unspecified.
        if offset>size or filesz>size-offset:raise ParseError('ELF_SEGMENT_OUTSIDE_FILE')
        if address+memsz>1<<bits:raise ParseError('ELF_VIRTUAL_ADDRESS_OVERFLOW')
        if ptype==1:
            if filesz>memsz:raise ParseError('ELF_LOAD_FILESZ_EXCEEDS_MEMSZ')
            if align>1 and (align&(align-1) or address%align!=offset%align):raise ParseError('ELF_LOAD_ALIGNMENT_UNSUPPORTED')
            loads.append((address,offset,filesz))
        elif ptype==2:dynamics.append((offset,filesz))
        elif ptype==3:interpreters.append((offset,filesz))
    if len(dynamics)>1 or len(interpreters)>1:raise ParseError('ELF_MULTIPLE_DYNAMIC_OR_INTERPRETER_SEGMENTS')
    def clean(raw,allow_empty=False):
        try:value=raw.decode('utf8')
        except UnicodeError:raise ParseError('ELF_METADATA_TEXT_NOT_UTF8') from None
        if not supported_text(value) or (not value and not allow_empty):raise ParseError('ELF_METADATA_TEXT_UNSUPPORTED')
        return value
    interpreter=''
    if interpreters:
        offset,count=interpreters[0]
        if count<2 or count>1025:raise ParseError('ELF_INTERPRETER_SIZE_UNSUPPORTED')
        raw=reader.read(offset,count)
        if raw[-1:]!=b'\0' or b'\0' in raw[:-1]:raise ParseError('ELF_INTERPRETER_NOT_TERMINATED')
        interpreter=clean(raw[:-1])
    result={'class':bits,'endian':endian,'machine':machine,'machine_name':MACHINES.get(machine,'unlisted'),
            'osabi':ident[7],'abi_version':ident[8],'flags':flags,'type':'EXEC' if kind==2 else 'DYN',
            'interpreter':interpreter,'soname':'','needed':[],'rpath':'','runpath':'',
            'metadata':'no_dynamic_segment' if not dynamics else 'dynamic_segment'}
    if not dynamics:return result
    offset,count=dynamics[0];entry_size=8 if bits==32 else 16
    if count==0 or count%entry_size or count//entry_size>4096:raise ParseError('ELF_DYNAMIC_SIZE_UNSUPPORTED')
    data=reader.read(offset,count);tags=defaultdict(list);terminated=False
    for i in range(0,count,entry_size):
        tag,value=struct.unpack_from(order+('iI' if bits==32 else 'qQ'),data,i)
        if tag==0:terminated=True;break
        if tag in (1,5,10,14,15,29):tags[tag].append(value)
    if not terminated:raise ParseError('ELF_DYNAMIC_NULL_MISSING')
    if len(tags[1])>256:raise ParseError('ELF_NEEDED_COUNT_LIMIT')
    for tag in (5,10,14,15,29):
        if len(tags[tag])>1:raise ParseError('ELF_DUPLICATE_SINGLETON_DYNAMIC_TAG')
    has_strings=any(tags[tag] for tag in (1,14,15,29))
    if has_strings or tags[5] or tags[10]:
        if len(tags[5])!=1 or len(tags[10])!=1:raise ParseError('ELF_STRING_TABLE_TAGS_MISSING')
        address=tags[5][0];length=tags[10][0]
        if not 1<=length<=MAX_STRTAB or address+length>1<<bits:raise ParseError('ELF_STRING_TABLE_SIZE_LIMIT')
        mappings={file_offset+address-start for start,file_offset,span in loads if start<=address and length<=span-(address-start)}
        if len(mappings)!=1:raise ParseError('ELF_STRING_TABLE_MAPPING_UNRESOLVED_OR_AMBIGUOUS')
        strings=reader.read(mappings.pop(),length)
        if strings[:1]!=b'\0':raise ParseError('ELF_STRING_TABLE_ZERO_ENTRY_MISSING')
        def get_string(index,allow_empty=False):
            if index>=length:raise ParseError('ELF_STRING_OFFSET_OUTSIDE_TABLE')
            end=strings.find(b'\0',index,min(length,index+1025))
            if end<0:raise ParseError('ELF_STRING_UNTERMINATED_OR_TOO_LONG')
            return clean(strings[index:end],allow_empty)
        result['needed']=[get_string(index) for index in tags[1]]
        for tag,key in [(14,'soname'),(15,'rpath'),(29,'runpath')]:
            if tags[tag]:result[key]=get_string(tags[tag][0],key in ('rpath','runpath'))
    budget.references+=len(result['needed'])
    if budget.references>MAX_REFERENCES:raise ScanLimit('TOTAL_NEEDED_REFERENCE_LIMIT')
    return result

def inspect_file(path,budget,hash_files=False,runtime_hints=False):
    """Read metadata and optionally hashes; reject observed source changes."""
    ordinary(path)
    before=path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):raise InspectorError('NON_REGULAR_INPUT')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno())
        # Windows path stat and handle fstat can give different ctime semantics.
        # Compare ctime within each API, keeping identity/size/mtime across APIs.
        if identity(before)!=identity(opened):raise InspectorError('FILE_CHANGED_BEFORE_READ')
        info=parse_stream(stream,before.st_size,budget)
        if info is not None:
            info['bytes']=before.st_size
            if runtime_hints:info['runtime_hint_scan']=scan_runtime_hints(stream,before.st_size,budget)
            if hash_files:
                stream.seek(0);hasher=hashlib.sha256();remaining=before.st_size
                while remaining:
                    count=min(1024*1024,remaining);budget.read(count,True);data=stream.read(count)
                    if len(data)!=count:raise InspectorError('FILE_CHANGED_DURING_HASH')
                    hasher.update(data);remaining-=count
                if stream.read(1):raise InspectorError('FILE_CHANGED_DURING_HASH')
                info['sha256']=hasher.hexdigest()
        if stamp(opened)!=stamp(os.fstat(stream.fileno())):raise InspectorError('FILE_CHANGED_DURING_READ')
    if stamp(before)!=stamp(path.stat(follow_symlinks=False)):raise InspectorError('FILE_CHANGED_AFTER_READ')
    return info

def analyze(roots=(),files=(),limits=None,hash_files=False,runtime_hints=False):
    """Find metadata candidates in explicit roots; does not emulate an OS loader."""
    limits=limits or Limits();budget=Budget(limits)
    if not roots and not files:raise InspectorError('SELECT_AT_LEAST_ONE_ROOT_OR_FILE')
    if len(roots)>8 or len(files)>32:raise InspectorError('TOO_MANY_ROOTS_OR_SELECTED_FILES')
    roots=[ordinary(p) for p in roots];files=[ordinary(p) for p in files]
    for root in roots:
        if not root.is_dir():raise InspectorError('ROOT_MUST_BE_DIRECTORY')
    for i,root in enumerate(roots):
        for other in roots[:i]:
            if root.is_relative_to(other) or other.is_relative_to(root):raise InspectorError('ROOTS_MUST_BE_DISJOINT')
    for path in files:
        if not path.is_file():raise InspectorError('SELECTED_FILE_MUST_BE_REGULAR')
    nodes={};issues=[];omitted=0;seen={};seeds=[];ignored=0
    def issue(label,code):
        nonlocal omitted
        if len(issues)<MAX_ISSUES:issues.append({'location':label,'code':code})
        else:omitted+=1
    def one(path,label,selected=False):
        nonlocal ignored
        key=path_key(path)
        if key in seen:
            if selected and seen[key] in nodes:seeds.append(seen[key])
            return
        budget.check()
        if budget.files>=limits.max_files:raise ScanLimit('FILE_COUNT_LIMIT')
        budget.files+=1;seen[key]=label
        if not supported_text(label):issue('unrepresentable-path','PATH_TEXT_UNSUPPORTED');return
        try:
            info=inspect_file(path,budget,hash_files,runtime_hints)
            if info is None:
                ignored+=1
                if selected:issue(label,'SELECTED_FILE_NOT_ELF')
            else:
                if len(nodes)>=MAX_ELFS:raise ScanLimit('ELF_COUNT_LIMIT')
                nodes[label]={'id':label,'name':path.name,**info}
                if runtime_hints:
                    for reason in info['runtime_hint_scan']['reasons']:issue(label,'RUNTIME_HINT_'+reason)
                if selected:seeds.append(label)
        except ScanLimit:raise
        except InspectorError as error:issue(label,str(error))
        except OSError:issue(label,'FILE_UNREADABLE')
    def walk(folder,label,depth):
        budget.check()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    budget.check()
                    if budget.entries>=limits.max_entries:raise ScanLimit('ENTRY_COUNT_LIMIT')
                    budget.entries+=1
                    child=label+'/'+entry.name
                    if not supported_text(child):issue(label,'PATH_TEXT_UNSUPPORTED');continue
                    try:
                        info=entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:issue(child,'LINK_OR_REPARSE_SKIPPED')
                        elif stat.S_ISDIR(info.st_mode):
                            if depth>=limits.max_depth:issue(child,'DEPTH_LIMIT')
                            else:walk(Path(entry.path),child,depth+1)
                        elif stat.S_ISREG(info.st_mode):one(Path(entry.path),child)
                        else:issue(child,'SPECIAL_FILE_SKIPPED')
                    except OSError:issue(child,'ENTRY_UNREADABLE')
        except OSError:issue(label,'DIRECTORY_UNREADABLE')
    try:
        for i,path in enumerate(files,1):one(path,'selected-'+str(i)+'/'+path.name,True)
        for i,root in enumerate(roots,1):walk(root,'root-'+str(i),0)
    except ScanLimit as error:issue('scan',str(error))
    if not nodes:issue('scan','NO_SUPPORTED_ELF_FILES')
    aliases=defaultdict(set)
    for node in nodes.values():
        for alias in (node['name'],node['soname']):
            if alias:aliases[alias].add(node['id'])
    if not files:seeds=sorted(nodes)
    seeds=sorted(set(seeds));queue=deque(seeds);visited=set();edges=[];stopped=False
    while queue and not stopped:
        try:budget.check()
        except ScanLimit as error:issue('graph',str(error));break
        identity_id=queue.popleft()
        if identity_id in visited:continue
        visited.add(identity_id);node=nodes[identity_id]
        for needed in node['needed']:
            if len(edges)>=MAX_REFERENCES:issue('graph','EDGE_COUNT_LIMIT');stopped=True;break
            candidates=sorted(aliases.get(needed,()))
            arch_matches=[name for name in candidates if all(nodes[name][k]==node[k] for k in ('class','endian','machine'))]
            compatible=[name for name in arch_matches if nodes[name]['type']=='DYN']
            status='unresolved_in_supplied_inputs';target=None
            if '/' in needed or '\\' in needed:status='path_dependency_not_resolved';compatible=[]
            elif len(compatible)>1:status='ambiguous_candidates'
            elif len(compatible)==1:status='unique_metadata_candidate';target=compatible[0];queue.append(target)
            elif arch_matches:status='object_type_mismatch'
            elif candidates:status='architecture_mismatch'
            shown=compatible if compatible else candidates
            edges.append({'consumer':identity_id,'needed':needed,'status':status,'candidate':target,
                          'candidate_count':len(shown),'candidates':shown[:MAX_CANDIDATES],
                          'candidates_omitted':max(0,len(shown)-MAX_CANDIDATES)})
    counts={key:sum(e['status']==key for e in edges) for key in ['unique_metadata_candidate','ambiguous_candidates','architecture_mismatch','object_type_mismatch','unresolved_in_supplied_inputs','path_dependency_not_resolved']}
    review=bool(issues or omitted or any(e['status']!='unique_metadata_candidate' for e in edges))
    result={'schema':'outlands-offline-elf-dependencies/1','tool_version':VERSION,'status':'REVIEW_REQUIRED' if review else 'NO_SCOPE_FINDINGS',
            'interpretation':'Candidates in explicit local inputs only. No loader, linker namespaces, symbol/ABI compatibility, dlopen or runtime success is verified.',
            'limits':{'files':limits.max_files,'entries':limits.max_entries,'depth':limits.max_depth,'seconds':limits.seconds},
            'summary':{'files_examined':budget.files,'directory_entries':budget.entries,'elf_files':len(nodes),'non_elf_ignored':ignored,
                       'visited_in_graph':len(visited),'dependency_edges':len(edges),'issue_count':len(issues)+omitted,'issues_omitted':omitted,
                       'metadata_bytes_read':budget.metadata_bytes,'hash_bytes_read':budget.hash_bytes,**counts},
            'roots':['root-'+str(i) for i in range(1,len(roots)+1)],'entry_files':seeds,
            'files':[nodes[key] for key in sorted(nodes)],'dependencies':sorted(edges,key=lambda e:(e['consumer'],e['needed'])),
            'issues':sorted(issues,key=lambda x:(x['location'],x['code']))}
    if runtime_hints:
        result['runtime_hints']={
            'interpretation':'ASCII token observations only. They may be unused, incomplete or coincidental; they do not prove dependencies, missing files, runtime loading or configuration use. No hinted path is opened.',
            'limits':{'file_bytes':MAX_HINT_FILE_BYTES,'total_bytes':MAX_HINT_TOTAL_BYTES,'ascii_run_bytes':MAX_HINT_STRING,
                      'observations_per_file':MAX_HINTS_PER_FILE,'total_observations':MAX_HINTS_TOTAL},
            'files_scanned':sum('runtime_hint_scan' in node for node in nodes.values()),
            'bytes_scanned':budget.hint_bytes,'observation_slots_used':budget.hint_count,
            'observations':sum(len(node['runtime_hint_scan']['observations']) for node in nodes.values()),
            'files_with_partial_hint_coverage':sum(node['runtime_hint_scan']['coverage']!='complete_ascii_scan' for node in nodes.values())}
    if len(encoded(result))>MAX_REPORT:raise InspectorError('JSON_REPORT_SIZE_LIMIT')
    return result

STYLE='body{font:16px/1.5 system-ui,sans-serif;margin:0;background:#edf3f7;color:#183044}main{max-width:1200px;margin:24px auto;background:white;padding:28px;border-top:6px solid #007c78}h1,h2{line-height:1.2}h2{margin-top:32px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cedbe3;padding:9px;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}.scroll{overflow:auto}.note{background:#e9f5f2;padding:14px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.metric{background:#edf3f7;padding:12px}.metric strong{display:block;font-size:26px}summary{cursor:pointer;padding:12px 0}nav a{margin-right:16px}code{overflow-wrap:anywhere}a{color:#006a86}@media(max-width:650px){main{padding:16px;margin:0}.metrics{grid-template-columns:repeat(2,1fr)}}'
def html_report(report):
    esc=lambda value:html.escape(str(value),quote=True)
    def table(headers,rows):
        return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    body='<h1>Offline ELF Dependency Inspector</h1><p class="note">'+esc(report['interpretation'])+'</p><h2>'+esc(report['status'].replace('_',' ').title())+'</h2>'
    body+='<nav><a href="#dependencies">Dependencies</a><a href="#metadata">File metadata</a><a href="#coverage">Coverage</a></nav><div class="metrics">'
    for key,label in [('elf_files','ELF files'),('dependency_edges','Dependency edges'),('unresolved_in_supplied_inputs','Unresolved'),('ambiguous_candidates','Ambiguous')]:
        body+='<div class="metric"><strong>'+esc(report['summary'][key])+'</strong>'+label+'</div>'
    body+='</div><details><summary>Full counts and read budgets</summary>'+table(['Summary','Count'],[(key.replace('_',' '),value) for key,value in report['summary'].items()])+'</details>'
    body+='<h2 id="dependencies">Declared dependencies</h2>'+table(['Consumer','DT_NEEDED','Finding','Candidate(s)'],[(e['consumer'],e['needed'],e['status'].replace('_',' '),'\n'.join(e['candidates'])+(' (additional candidates omitted)' if e['candidates_omitted'] else '')) for e in report['dependencies']])
    if not report['dependencies']:body+='<p>No declared dependencies were visited in this inspection.</p>'
    body+='<h2 id="metadata">Inspected ELF metadata</h2>'+table(['File','Architecture','SONAME','Interpreter','RPATH / RUNPATH'],[(f['id'],f"{f['class']}-bit {f['endian']} {f['machine_name']} ({f['machine']})",f['soname'],f['interpreter'],f['rpath']+'\n'+f['runpath']) for f in report['files']])
    if 'runtime_hints' in report:
        body+='<h2 id="runtime-hints">Optional runtime text hints</h2><p class="note">'+esc(report['runtime_hints']['interpretation'])+'</p>'
        body+=table(['File','Kind','Observed token','First byte offset','Occurrences'],[(f['id'],hint['kind'],hint['text'],hint['first_offset'],hint['occurrences']) for f in report['files'] for hint in f['runtime_hint_scan']['observations']])
        body+=table(['File','Hint coverage','Bytes scanned / file bytes','Omission reasons'],[(f['id'],f['runtime_hint_scan']['coverage'],str(f['runtime_hint_scan']['bytes_scanned'])+' / '+str(f['bytes']),', '.join(f['runtime_hint_scan']['reasons'])) for f in report['files']])
    body+='<h2 id="coverage">Coverage issues</h2>'+table(['Location','Code'],[(i['location'],i['code']) for i in report['issues']])
    if not report['issues']:body+='<p>No coverage issues recorded.</p>'
    body+='<p>Private inspection output: relative names, dependency names, embedded search/interpreter paths and optional hint tokens can identify your project. Review before sharing. See report.json for complete machine-readable metadata. No inspected binaries are included.</p>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\';style-src \'unsafe-inline\';base-uri \'none\';form-action \'none\'"><title>Offline ELF dependency report</title><style>'+STYLE+'</style></head><body><main>'+body+'</main></body></html>').encode('utf8')

def output_path(value,roots):
    path=ordinary(value,False);ordinary(path.parent)
    if path.exists():raise InspectorError('OUTPUT_MUST_BE_NEW_DIRECTORY')
    if any(path.is_relative_to(ordinary(root)) for root in roots):raise InspectorError('OUTPUT_MUST_BE_OUTSIDE_SCAN_ROOTS')
    return path

def write_report(report,destination,roots=()):
    target=output_path(destination,roots)
    members={'report.json':encoded(report),'index.html':html_report(report),
             'README.txt':b'Private local metadata report. No inspected binaries are included. This is not a backup, runtime compatibility check or software license clearance. Review filenames, embedded paths and any optional hint tokens before sharing.\n'}
    if sum(map(len,members.values()))>MAX_REPORT:raise InspectorError('COMBINED_REPORT_SIZE_LIMIT')
    members['MANIFEST.json']=encoded({'schema':'outlands-elf-report-files/1','files':[{'path':name,'bytes':len(data),'sha256':digest(data)} for name,data in sorted(members.items())]})
    target.mkdir(mode=0o700)
    for name,data in members.items():
        with (target/name).open('xb') as stream:stream.write(data)
        if (target/name).read_bytes()!=data:raise InspectorError('OUTPUT_READBACK_MISMATCH')
    return {'files':len(members),'bytes':sum(map(len,members.values()))}

def cli(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--root',action='append',default=[],metavar='DIRECTORY',help='Repeat for up to eight disjoint dependency search roots')
    parser.add_argument('--file',action='append',default=[],metavar='ELF',help='Repeat for selected entry files; otherwise every inspected ELF is an entry')
    parser.add_argument('--output',metavar='NEW_DIRECTORY',help='Write a new private HTML/JSON report folder; otherwise JSON goes to stdout')
    parser.add_argument('--sha256',action='store_true',help='Hash inspected ELF bytes within a separate 512 MiB read budget')
    parser.add_argument('--runtime-hints',action='store_true',help='Opt in to bounded ASCII .so and selected config/firmware path observations; never declared dependencies')
    parser.add_argument('--max-files',type=int,default=2000)
    parser.add_argument('--max-entries',type=int,default=20000)
    parser.add_argument('--max-depth',type=int,default=32)
    parser.add_argument('--seconds',type=int,default=60)
    args=parser.parse_args(argv)
    try:
        if args.output:output_path(args.output,args.root)
        report=analyze(args.root,args.file,Limits(args.max_files,args.max_entries,args.max_depth,args.seconds),args.sha256,args.runtime_hints)
        if args.output:
            result=write_report(report,args.output,args.root)
            print(json.dumps({'status':report['status'],'report_files':result['files'],'summary':report['summary']}))
        else:print(encoded(report).decode('utf8'),end='')
        return 2 if report['status']=='REVIEW_REQUIRED' else 0
    except InspectorError as error:print(json.dumps({'status':'ERROR','code':str(error)}),file=sys.stderr);return 1
    except OSError:print(json.dumps({'status':'ERROR','code':'FILESYSTEM_OPERATION_FAILED_PARTIAL_NEW_OUTPUT_MAY_REMAIN'}),file=sys.stderr);return 1
    except KeyboardInterrupt:print(json.dumps({'status':'CANCELLED','code':'PARTIAL_NEW_OUTPUT_MAY_REMAIN'}),file=sys.stderr);return 130

if __name__=='__main__':raise SystemExit(cli())
