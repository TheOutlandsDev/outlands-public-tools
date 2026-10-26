"""Create tiny original fictional sparse-image fixtures in a new directory. MIT."""
from pathlib import Path
import os
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, TextError, canonical_directory, cli_error, local_path, no_links, require


def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv)
        output=local_path(args.output)
        parent=canonical_directory(output.parent)
        require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS')
        output=parent/output.name
        header=struct.pack('<IHHHHIIII',0xED26FF3A,1,0,28,12,4,4,3,0)
        raw=struct.pack('<HHII',0xCAC1,0,1,16)+b'DEMO'
        fill=struct.pack('<HHII',0xCAC2,0,1,16)+b'ABCD'
        hole=struct.pack('<HHII',0xCAC3,0,2,12)
        valid=header+raw+fill+hole
        checksum_header=struct.pack('<IHHHHIIII',0xED26FF3A,1,0,28,12,4,4,4,0)
        crc=struct.pack('<HHII',0xCAC4,0,0,16)+b'\0'*4
        data={'valid.sparse':valid,'crc-unverified.sparse':checksum_header+raw+fill+hole+crc,
              'truncated.sparse':valid[:-1]}
        output.mkdir(mode=0o700,exist_ok=False)
        for name,payload in data.items():
            no_links(output)
            fd=os.open(output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
            with os.fdopen(fd,'wb') as stream:
                stream.write(payload)
        print('{"status":"GENERATED","files":3}')
        return 0
    except (TextError,OSError,ValueError) as error:
        return cli_error(error)


if __name__=='__main__':
    raise SystemExit(main())
