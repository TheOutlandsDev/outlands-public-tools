"""Create authored fictional text examples only; never execute these configs. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from text_support import Parser, TextError, canonical_directory, cli_error, local_path, require
FILES = {'clean.rc': '# Fictional declarations only; executable does not exist.\nservice demo_worker /fictional/bin/worker --demo\n    class main\n    disabled\n    oneshot\non boot\n    start demo_worker\n', 'review.rc': '# Deliberately incomplete selected-file evidence.\nservice demo_worker /fictional/bin/worker\n    critical\n    onrestart reboot\nservice demo_worker /fictional/bin/other\n    override\non boot\n    start demo_worker\n    start unselected_service\n    mount_all /fictional/fstab --early\nimport /fictional/not-followed.rc\n'}

def main(argv=None):
    parser=Parser(description=__doc__); parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv); output=local_path(args.output)
        parent=canonical_directory(output.parent); output=parent/output.name
        require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS')
        output.mkdir(mode=0o700,exist_ok=False)
        for name,text in FILES.items():
            with (output/name).open('x',encoding='utf-8',newline='\n') as stream: stream.write(text)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':len(FILES)},sort_keys=True)); return 0
    except (TextError,OSError,ValueError) as error: return cli_error(error)

if __name__=='__main__': raise SystemExit(main())
