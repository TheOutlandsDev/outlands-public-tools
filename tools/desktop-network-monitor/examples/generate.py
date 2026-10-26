"""Generate fictional metadata in a new explicit directory. Original MIT."""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,local_path,canonical_directory,require,cli_error

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);target=local_path(args.output);parent=canonical_directory(target.parent)
        require(not target.exists() and not target.is_symlink(),'OUTPUT_EXISTS');target=parent/target.name
        target.mkdir(mode=0o700,exist_ok=False)
        rows=[{'source':'192.0.2.10','destination':'198.51.100.20','protocol':'TCP','source_port':50000,'destination_port':443,'bytes':100},
              {'source':'192.0.2.10','destination':'203.0.113.30','protocol':'TCP','source_port':50001,'destination_port':23,'bytes':60}]
        data=(json.dumps({'schema':'outlands-packet-metadata/1','packets':rows},indent=2)+'\n').encode()
        fd=os.open(target/'packets.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':1}));return 0
    except Exception as error:return cli_error(error)
if __name__=='__main__':raise SystemExit(main())
