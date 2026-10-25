"""Create original metadata-only ELF fixtures, never executable machine code."""
from pathlib import Path
import argparse
import os
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from elf_inspector import InspectorError, ordinary

def make_elf(needed=(),soname='',bits=64,endian='little',machine=None,runpath='',rpath='',interpreter='',dynamic=True,extra_tags=()):
    """Small authored ELF metadata fixture; no compiler output or third-party bytes."""
    if bits not in (32,64) or endian not in ('little','big'):raise ValueError('Fixture format')
    order='<' if endian=='little' else '>';machine=machine if machine is not None else (183 if bits==64 else 40)
    strings=bytearray(b'\0');tags=[]
    def add(tag,value):
        position=len(strings);strings.extend(value.encode('utf8')+b'\0');tags.append((tag,position))
    for name in needed:add(1,name)
    if soname:add(14,soname)
    if runpath:add(29,runpath)
    if rpath:add(15,rpath)
    entry_size=8 if bits==32 else 16;dyn_offset=512;base=65536
    dyn_size=(len(tags)+len(extra_tags)+3)*entry_size
    string_offset=((dyn_offset+dyn_size+63)//64)*64
    interpreter_bytes=interpreter.encode('utf8')+b'\0' if interpreter else b''
    interp_offset=((string_offset+len(strings)+63)//64)*64
    total=max(string_offset+len(strings),interp_offset+len(interpreter_bytes))
    ehsize=52 if bits==32 else 64;phsize=32 if bits==32 else 56
    count=1+int(dynamic)+int(bool(interpreter));blob=bytearray(total)
    blob[:16]=b'\x7fELF'+bytes([1 if bits==32 else 2,1 if endian=='little' else 2,1,0,0])+bytes(7)
    header=(3,machine,1,0,ehsize,0,0,ehsize,phsize,count,0,0,0)
    struct.pack_into(order+('HHIIIIIHHHHHH' if bits==32 else 'HHIQQQIHHHHHH'),blob,16,*header)
    phs=[(1,0,base,total)]
    if dynamic:phs.append((2,dyn_offset,base+dyn_offset,dyn_size))
    if interpreter:phs.append((3,interp_offset,base+interp_offset,len(interpreter_bytes)))
    for i,(ptype,offset,address,size) in enumerate(phs):
        values=(ptype,offset,address,0,size,size,4,1) if bits==32 else (ptype,4,offset,address,0,size,size,1)
        struct.pack_into(order+('IIIIIIII' if bits==32 else 'IIQQQQQQ'),blob,ehsize+i*phsize,*values)
    if dynamic:
        entries=tags+[(5,base+string_offset),(10,len(strings))]+list(extra_tags)+[(0,0)]
        for i,pair in enumerate(entries):struct.pack_into(order+('iI' if bits==32 else 'qQ'),blob,dyn_offset+i*entry_size,*pair)
    blob[string_offset:string_offset+len(strings)]=strings
    if interpreter:blob[interp_offset:interp_offset+len(interpreter_bytes)]=interpreter_bytes
    return bytes(blob)

def create(destination,clean=False,runtime_hints=False):
    root=ordinary(destination,False);ordinary(root.parent)
    if root.exists():raise InspectorError('DEMO_DESTINATION_MUST_BE_NEW')
    root.mkdir(mode=0o700);(root/'app').mkdir();(root/'lib').mkdir()
    needed=['libdemo.so'] if clean else ['libdemo.so','libchoice.so','libabsent.so','libwrong.so']
    members={'app/demo.elf':make_elf(needed,runpath='$ORIGIN/../lib',interpreter='/fictional/linker64'),
             'lib/libdemo-real.so':make_elf(['libleaf.so'],'libdemo.so'),
             'lib/libleaf.so':make_elf(['libdemo.so'],'libleaf.so'),
             'lib/not-elf.txt':b'Fictional non-ELF file; ignored by metadata discovery.\n'}
    if not clean:
        members.update({'lib/choice-a.so':make_elf(soname='libchoice.so'),'lib/choice-b.so':make_elf(soname='libchoice.so'),
                        'lib/libwrong.so':make_elf(soname='libwrong.so',bits=32)})
    if runtime_hints:
        members['app/demo.elf']+=b'\0liboptional_effects.so.2\0/vendor/etc/fictional-demo.xml\0/vendor/firmware/fictional-demo.bin\0'
    for name,data in members.items():
        fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
    return {'files':len(members),'fixture':'clean' if clean else 'mixed','machine_code':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',required=True);parser.add_argument('--clean',action='store_true')
    parser.add_argument('--runtime-hints',action='store_true',help='Append invented optional-library/config/firmware tokens, never dependencies')
    args=parser.parse_args()
    try:
        import json
        print(json.dumps(create(args.destination,args.clean,args.runtime_hints)));return 0
    except (InspectorError,OSError):print('Could not create demo; use a new local directory with an existing parent.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
