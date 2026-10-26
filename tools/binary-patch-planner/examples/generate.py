"""Generate fictional binary files and exact patch plans; never inspect real data. MIT."""
from pathlib import Path
import hashlib
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, TextError, canonical_directory, cli_error, local_path, no_links, require

SOURCE = b'ORCHARD-DEMO-v1\n'

def plan():
    return {'schema_version':1,'source':{'bytes':len(SOURCE),'sha256':hashlib.sha256(SOURCE).hexdigest()},
        'patches':[{'offset':8,'expected_hex':b'DEMO'.hex(),'replacement_hex':b'TEST'.hex()},
                   {'offset':13,'expected_hex':b'v1'.hex(),'replacement_hex':b'v2'.hex()}]}

def generate(value):
    target=local_path(value);parent=canonical_directory(target.parent)
    require(not target.exists() and not target.is_symlink(),'OUTPUT_EXISTS')
    target=parent/target.name
    clean=plan();mismatch=plan();mismatch['patches'][0]['expected_hex']=b'NOPE'.hex()
    overlap=plan();overlap['patches'].append({'offset':10,'expected_hex':b'MO'.hex(),'replacement_hex':b'XY'.hex()})
    values={'source.bin':SOURCE,'verified-plan.json':clean,'unexpected-plan.json':mismatch,'overlap-plan.json':overlap}
    target.mkdir(mode=0o700,exist_ok=False)
    for name,value in values.items():
        data=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode('utf-8')
        no_links(target)
        fd=os.open(target/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
    return len(values)

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);count=generate(args.output)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':count}));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)

if __name__=='__main__':raise SystemExit(main())
