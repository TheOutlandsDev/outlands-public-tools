"""Read-only changed-path gate for a publisher after all qualification succeeds."""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess

def requested(event_name,ref,sha,event,patterns,git):
    if ref!='refs/heads/main':return False
    if event_name=='workflow_dispatch':return True
    if event_name!='push':return False
    before=event.get('before','')
    if not re.fullmatch('[0-9a-f]{40}',before) or before=='0'*40 or not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('EXACT_EXISTING_MAIN_BASE_REQUIRED')
    changed=git(before,sha)
    return any(fnmatch.fnmatchcase(name,pattern) for name in changed for pattern in patterns)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--path',action='append',required=True);args=p.parse_args()
    def paths(before,after):
        raw=subprocess.check_output(['git','diff','--no-renames','--name-only','-z',before,after,'--'])
        return [name.decode('utf-8') for name in raw.split(b'\0') if name]
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    value=requested(os.environ['GITHUB_EVENT_NAME'],os.environ['GITHUB_REF'],os.environ['GITHUB_SHA'],event,args.path,paths)
    with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as out:out.write('publish_requested='+str(value).lower()+'\n')
    print(json.dumps({'publish_requested':value,'workflow_only_changes_do_not_replace_assets':True}))

if __name__=='__main__':main()
