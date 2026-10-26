"""Create two small fictional source profiles in one fresh directory. MIT."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,no_links,require

FIXTURES={
    'orchard/README.txt':b'Fictional Orchard profile. This is not an installable game mod.\n',
    'orchard/config/demo.ini':b'[fictional]\ncolor=orange\nmode=orchard\n',
    'meadow/README.txt':b'Fictional Meadow profile. This is not an installable game mod.\n',
    'meadow/config/demo.ini':b'[fictional]\ncolor=green\nmode=meadow\n',
}


def generate(value):
    target=local_path(value);parent=canonical_directory(target.parent)
    require(not target.exists() and not target.is_symlink(),'OUTPUT_EXISTS')
    target=parent/target.name;target.mkdir(mode=0o700,exist_ok=False)
    for relative,data in FIXTURES.items():
        path=target/relative;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);no_links(path.parent)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
    return {'status':'FICTIONAL_EXAMPLES_CREATED','profiles':2,'files':len(FIXTURES)}


def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        result=generate(parser.parse_args(argv).output);print(json.dumps(result,sort_keys=True));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())
