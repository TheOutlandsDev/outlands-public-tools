"""Create authored fictional text exports only. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,require
FILES={'before.prop': '# Fictional values only.\nro.demo.name=Example\npersist.demo.rate=10\n', 'same.prop': '# Reordered whitespace/comment change.\npersist.demo.rate = 10\nro.demo.name=Example\n', 'changed.prop': 'ro.demo.name=Example\npersist.demo.rate=20\nro.demo.extra=enabled\n', 'review.prop': 'ro.demo.name=Example\npersist.demo.rate=10\npersist.demo.rate=20\nimport /fictional/not-followed.prop\n'}

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
