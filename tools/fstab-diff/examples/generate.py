"""Create authored fictional text examples only; never execute these configs. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from text_support import Parser, TextError, canonical_directory, cli_error, local_path, require
FILES = {'linux-before.fstab': '# Fictional records; never mount these.\nUUID=demo-root / ext4 defaults 0 1\nUUID=demo-data /srv/demo ext4 rw,noatime 0 2\n', 'linux-same.fstab': '# Comment-only change.\nUUID=demo-root / ext4 defaults 0 1\nUUID=demo-data /srv/demo ext4 rw,noatime 0 2\n', 'linux-changed.fstab': 'UUID=demo-data /srv/demo ext4 ro,noatime 0 2\nUUID=demo-root / ext4 defaults 0 1\nUUID=demo-extra /srv/extra ext4 defaults 0 2\n', 'android-before.fstab': '# Fictional Android fields.\n/dev/fictional/data /data ext4 noatime,nosuid wait,check\n', 'android-same.fstab': '/dev/fictional/data /data ext4 noatime,nosuid wait,check\n', 'android-changed.fstab': '/dev/fictional/data /data ext4 noatime,nosuid wait,check,quota\n', 'ambiguous.fstab': 'fictional-a /srv/demo ext4 rw 0 0\nfictional-b /srv/demo ext4 ro 0 0\n'}

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
