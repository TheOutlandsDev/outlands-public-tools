"""Check a pinned source inventory or create a deterministic, new-only source ZIP."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import zipfile
from ml_workbench import runtime

ROOT=Path(__file__).resolve().parent
MANIFEST='SOURCE-MANIFEST.json'


def verify():
    value=runtime.decode(runtime.read_bytes(ROOT/MANIFEST))
    if set(value)!={'format','files'} or value['format']!='outlands-source-inventory-v1':raise ValueError('SOURCE_MANIFEST_INVALID')
    paths=set()
    for relative,item in value['files'].items():
        name=Path(relative)
        if name.is_absolute() or '..' in name.parts or '\\' in relative or relative==MANIFEST:raise ValueError('SOURCE_PATH_INVALID')
        raw=runtime.read_bytes(ROOT/name)
        if item!={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:raise ValueError('SOURCE_BYTES_CHANGED')
        paths.add(relative)
    actual=set()
    for path in ROOT.rglob('*'):
        if '__pycache__' in path.parts:continue
        info=path.lstat()
        if path.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('SOURCE_LINK_REFUSED')
        if stat.S_ISREG(info.st_mode):actual.add(path.relative_to(ROOT).as_posix())
        elif not stat.S_ISDIR(info.st_mode):raise ValueError('SOURCE_SPECIAL_FILE_REFUSED')
    if actual!=paths|{MANIFEST}:raise ValueError('SOURCE_INVENTORY_CHANGED')
    return sorted(actual)


def package(output):
    paths=verify();buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in paths:
            info=zipfile.ZipInfo('ml-experiment-workbench/'+name,(2020,1,1,0,0,0))
            info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,runtime.read_bytes(ROOT/name),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    verify()
    raw=buffer.getvalue();runtime.write_new(Path(output),raw)
    return dict(files=len(paths),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser=runtime.Parser(prog='workbench-source',allow_abbrev=False)
    parser.add_argument('command',choices=('check','package'));parser.add_argument('--output')
    args=parser.parse_args()
    if args.command=='check':return dict(status='SOURCE_MATCH',files=len(verify()))
    if not args.output:raise ValueError('OUTPUT_REQUIRED')
    return package(args.output)


if __name__=='__main__':
    try:print(json.dumps(main(),sort_keys=True))
    except Exception:
        print(json.dumps(dict(error='SOURCE_OPERATION_REFUSED')));sys.exit(2)
