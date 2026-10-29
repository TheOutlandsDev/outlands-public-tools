import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import check_workflows as policy

class WorkflowPolicy(unittest.TestCase):
    def sample(self,publish=False):
        return {'on':{'push':{'branches':['**' if publish else 'main'],'paths':['sample/**']},'pull_request':{'paths':['sample/**']}},'concurrency':{'group':policy.GROUP,'cancel-in-progress':policy.CANCEL},'jobs':{'check':{'permissions':{'contents':'write' if publish else 'read'}}}}
    def test_current_repository_policy_and_yaml(self):
        self.assertGreaterEqual(policy.check(policy.ROOT)['workflows'],75)
    def test_normal_checks_and_qualified_release_branches(self):
        policy.validate(self.sample(),'sample.yml');policy.validate(self.sample(True),'sample.yml')
    def test_tag_fanout_is_refused(self):
        value=self.sample();value['on']['push']['tags']=['*']
        with self.assertRaisesRegex(ValueError,'ONLY_INTENTIONAL_RELEASE_TAGS'):policy.validate(value,'sample.yml')
    def test_missing_branch_filter_is_refused(self):
        value=self.sample();del value['on']['push']['branches']
        with self.assertRaisesRegex(ValueError,'BRANCH_FILTER_REQUIRED'):policy.validate(value,'sample.yml')
    def test_ordinary_branch_push_duplicate_is_refused(self):
        value=self.sample();value['on']['push']['branches']=['**']
        with self.assertRaisesRegex(ValueError,'BRANCH_FILTER_REQUIRED'):policy.validate(value,'sample.yml')
    def test_main_and_tag_cancellation_is_refused(self):
        for replacement in ('true',"${{ true }}", "${{ github.ref != '' }}"):
            value=self.sample();value['concurrency']['cancel-in-progress']=replacement
            with self.assertRaisesRegex(ValueError,'PROTECTED_RELEASE_CONCURRENCY_REQUIRED'):policy.validate(value,'sample.yml')
    def test_main_pending_run_replacement_is_refused(self):
        value=self.sample();value['concurrency']['group']='${{ github.workflow }}-${{ github.ref }}'
        with self.assertRaisesRegex(ValueError,'PROTECTED_RELEASE_CONCURRENCY_REQUIRED'):policy.validate(value,'sample.yml')
    def test_explicit_release_tags_remain_supported(self):
        value=self.sample(True);value['on']['push']['tags']=['toolkit-v*'];policy.validate(value,'toolkit-packages.yml')
    def test_missing_pr_checks_are_refused(self):
        value=self.sample();del value['on']['pull_request']
        with self.assertRaisesRegex(ValueError,'PR_CHECKS_REQUIRED'):policy.validate(value,'sample.yml')
    def test_duplicate_yaml_keys_are_refused(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_YAML_KEY'):policy.load('name: first\nname: second\n')
    def test_invalid_yaml_and_implicit_trigger_list_are_refused(self):
        with self.assertRaises(Exception):policy.load('on: [unterminated')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_TRIGGERS_REQUIRED'):policy.validate(policy.load('on: [push, pull_request]'),'sample.yml')

if __name__=='__main__':unittest.main()
