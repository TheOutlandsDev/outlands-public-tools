"""Check YAML and the repository's bounded Actions trigger/concurrency policy."""
import argparse
import json
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
GROUP="${{ github.workflow }}-${{ (github.ref == 'refs/heads/main' || github.ref_type == 'tag') && github.run_id || github.event.pull_request.head.repo.full_name || github.repository }}-${{ github.head_ref || github.ref_name }}"
CANCEL="${{ github.event_name == 'pull_request' || (github.ref_type == 'branch' && github.ref_name != 'main') }}"
TAGS={'toolkit-packages.yml':['toolkit-v*'],'site-builder-release.yml':['local-site-builder-v*']}

class StrictLoader(yaml.BaseLoader):
    pass

def mapping(loader,node,deep=False):
    result={}
    for key,value in node.value:
        name=loader.construct_object(key,deep=deep)
        if name in result:raise ValueError('DUPLICATE_YAML_KEY')
        result[name]=loader.construct_object(value,deep=deep)
    return result

StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)

def load(text):
    return yaml.load(text,Loader=StrictLoader)

def publisher(document,name):
    return name in TAGS or any(job.get('permissions',{}).get('contents')=='write' for job in document.get('jobs',{}).values())

def validate(document,name):
    if not isinstance(document,dict) or not isinstance(document.get('on'),dict):raise ValueError('EXPLICIT_TRIGGERS_REQUIRED')
    events=document['on']
    if 'pull_request_target' in events:raise ValueError('PR_TARGET_NOT_AUTHORIZED')
    push=events.get('push')
    if not isinstance(push,dict) or push.get('branches')!=['**' if publisher(document,name) else 'main']:raise ValueError('BRANCH_FILTER_REQUIRED')
    if push.get('tags',[])!=TAGS.get(name,[]):raise ValueError('ONLY_INTENTIONAL_RELEASE_TAGS')
    if not isinstance(push.get('paths'),list) or not push['paths']:raise ValueError('PATH_FILTER_REQUIRED')
    if not isinstance(events.get('pull_request'),dict) or not events['pull_request'].get('paths'):raise ValueError('PR_CHECKS_REQUIRED')
    if document.get('concurrency')!={'group':GROUP,'cancel-in-progress':CANCEL}:raise ValueError('PROTECTED_RELEASE_CONCURRENCY_REQUIRED')
    if not document.get('jobs'):raise ValueError('JOBS_REQUIRED')
    if name not in TAGS:
        for job in document['jobs'].values():
            for step in job.get('steps',[]):
                if 'publish.py' in step.get('run',''):
                    if step.get('if')!="steps.publication_scope.outputs.publish_requested == 'true'" or not any(s.get('id')=='publication_scope' for s in job['steps']):raise ValueError('WORKFLOW_ONLY_PUBLICATION_GUARD_REQUIRED')

def check(root):
    paths=sorted((root/'.github/workflows').glob('*.yml'))
    if not paths:raise ValueError('WORKFLOWS_REQUIRED')
    for path in paths:
        try:validate(load(path.read_text(encoding='utf-8')),path.name)
        except (ValueError,yaml.YAMLError) as error:raise ValueError(path.name+': '+str(error)) from None
    return dict(status='PASS',workflows=len(paths),protected_refs=['main','intentional release tags'],ordinary_push_branch='main',superseded_branch_runs_cancel=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);args=p.parse_args();print(json.dumps(check(args.root)))
