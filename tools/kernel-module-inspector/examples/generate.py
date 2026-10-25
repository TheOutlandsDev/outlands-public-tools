"""Create authored fictional metadata only; never deploy these configurations. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,require
FILES={'clean.dep': '# Fictional metadata only; no module binaries.\nfictional/core.ko:\nfictional/helper.ko: fictional/core.ko\nfictional/feature.ko: fictional/helper.ko fictional/core.ko\n', 'clean.load': 'feature\n', 'available.txt': 'fictional/core.ko\nfictional/helper.ko\nfictional/feature.ko\n', 'review.dep': 'fictional/a.ko: fictional/b.ko\nfictional/b.ko: fictional/a.ko\nfictional/other.ko: fictional/unselected.ko\n', 'review.load': 'a\na\nnot_declared\n'}

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);output=local_path(args.output);parent=canonical_directory(output.parent);output=parent/output.name
        require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS');output.mkdir(mode=0o700,exist_ok=False)
        for name,text in FILES.items():
            with (output/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':len(FILES)},sort_keys=True));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)

if __name__=='__main__':raise SystemExit(main())
