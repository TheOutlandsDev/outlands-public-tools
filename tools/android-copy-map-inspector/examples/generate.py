"""Create authored fictional text examples only; never execute these configs. MIT."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from text_support import Parser, TextError, canonical_directory, cli_error, local_path, require
FILES = {'clean.mk': '# Fictional source/destination declarations; no payload files.\nPRODUCT_COPY_FILES += \\\n    fictional/alpha.conf:vendor/etc/alpha.conf \\\n    fictional/beta.conf:vendor/etc/beta.conf:demo_owner\n', 'review.mk': 'PRODUCT_COPY_FILES += fictional/one:vendor/etc/demo fictional/two:vendor/etc/demo\nPRODUCT_COPY_FILES += fictional/three:Vendor/etc/Demo\nPRODUCT_COPY_FILES += fictional/four:../escape\nPRODUCT_COPY_FILES += $(UNKNOWN_ROOT)/five:vendor/etc/five\ninclude fictional-not-followed.mk\n', 'roots.mk': 'PRODUCT_COPY_FILES += $(LOCAL_PATH)/demo.conf:$(TARGET_COPY_OUT_VENDOR)/etc/demo.conf\n', 'roots.json': '{\n  "schema_version": 1,\n  "roots": {\n    "LOCAL_PATH": "fictional",\n    "TARGET_COPY_OUT_VENDOR": "vendor"\n  }\n}\n'}

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
