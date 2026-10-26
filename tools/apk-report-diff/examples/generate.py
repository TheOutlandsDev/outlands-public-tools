"""Create fictional saved badging text in one fresh directory. Original MIT."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, TextError, canonical_directory, cli_error, local_path, no_links, require

BEFORE="""package: name='example.orchard' versionCode='1' versionName='1.0' platformBuildVersionCode='34'
sdkVersion:'23'
targetSdkVersion:'34'
uses-library:'example.alpha'
uses-library-not-required:'example.beta'
application: label='Fictional Orchard' icon='res/demo.png'
"""
AFTER="""package: name='example.orchard' versionCode='2' versionName='2.0' platformBuildVersionCode='35'
sdkVersion:'23'
targetSdkVersion:'35'
uses-library:'example.beta'
uses-library-not-required:'example.gamma'
application: label='Fictional Orchard' icon='res/demo.png'
"""

def main(argv=None):
    parser=Parser(description=__doc__); parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv); output=local_path(args.output)
        parent=canonical_directory(output.parent); require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS')
        output=parent/output.name; output.mkdir(mode=0o700,exist_ok=False)
        values={'before.txt':BEFORE,'same.txt':BEFORE,'after.txt':AFTER,
                'unsupported.txt':AFTER+"future-metadata: 'fictional-only'\n",
                'duplicate.txt':AFTER+"uses-library:'example.beta'\n"}
        for name,text in values.items():
            no_links(output)
            fd=os.open(output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream: stream.write(text.encode('utf-8'))
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':len(values)})); return 0
    except (TextError,OSError,ValueError) as error: return cli_error(error)

if __name__=='__main__': raise SystemExit(main())
