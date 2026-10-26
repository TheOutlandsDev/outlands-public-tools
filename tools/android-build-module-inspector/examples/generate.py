"""Write fictional build text into a new private directory. Original MIT."""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,no_links,require

BP='''// Fictional declarations, not an actual Android project.
cc_library {
    name: "example.alpha",
    srcs: ["invented.cpp"],
    target: { android: { enabled: true, }, },
}
java_library { name: "example.beta", srcs: ["Invented.java"], }
'''
MK='''# Fictional declaration only; never included or built.
LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := example.gamma
LOCAL_SRC_FILES := invented.cpp
include $(BUILD_SHARED_LIBRARY)
'''
REVIEW='''cc_library { name: "example.alpha", }
cc_library { name: "example.alpha", }
cc_library { name: prefix + ".dynamic", }
'''

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);path=local_path(args.output);parent=canonical_directory(path.parent)
        require(not path.exists() and not path.is_symlink(),'OUTPUT_EXISTS');path=parent/path.name
        files={'clean.bp':BP,'clean.mk':MK,'review.bp':REVIEW,
               'wanted.txt':'example.alpha\nexample.beta\nexample.gamma\n',
               'wanted-unseen.txt':'example.alpha\nexample.unseen\n'}
        path.mkdir(mode=0o700,exist_ok=False)
        for name,value in files.items():
            no_links(path);fd=os.open(path/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(value.encode('utf-8'))
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':len(files)}));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)

if __name__=='__main__':raise SystemExit(main())
