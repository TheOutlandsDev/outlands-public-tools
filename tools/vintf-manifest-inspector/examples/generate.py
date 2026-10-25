"""Create authored fictional metadata only; never deploy these configurations. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,require
FILES={'clean.xml': '<manifest version="2.0" type="device" target-level="7">\n <hal format="hidl"><name>example.hardware.demo</name><transport>hwbinder</transport><version>2.1</version><interface><name>IDemo</name><instance>default</instance></interface></hal>\n <hal format="aidl"><name>example.hardware.helper</name><version>1</version><fqname>IHelper/default</fqname></hal>\n</manifest>\n', 'same.xml': '<!-- Authored equivalent declaration forms. -->\n<manifest version="2.0" type="device" target-level="7">\n <hal><name>example.hardware.demo</name><transport>hwbinder</transport><fqname>@2.1::IDemo/default</fqname></hal>\n <hal format="aidl"><name>example.hardware.helper</name><version>1</version><interface><name>IHelper</name><instance>default</instance></interface></hal>\n</manifest>\n', 'changed.xml': '<manifest version="2.0" type="device" target-level="7">\n <hal><name>example.hardware.demo</name><transport arch="64">passthrough</transport><fqname>@2.1::IDemo/default</fqname></hal>\n <hal format="aidl"><name>example.hardware.helper</name><version>2</version><fqname>IHelper/default</fqname></hal>\n</manifest>\n', 'review.xml': '<?fictional instruction?>\n<manifest version="2.0" type="device">\n <hal override="true"><name>example.hardware.demo</name><transport>hwbinder</transport><fqname>@2.1::IDemo/default</fqname><fqname>@2.1::IDemo/default</fqname></hal>\n <kernel version="fictional"/>\n</manifest>\n'}

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
