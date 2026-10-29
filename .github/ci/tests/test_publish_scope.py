from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from publish_scope import requested

class PublicationScope(unittest.TestCase):
    def check(self,names,**kw):
        return requested(kw.get('event','push'),kw.get('ref','refs/heads/main'),'b'*40,{'before':kw.get('before','a'*40)},['downloads/sample/**'],lambda a,b:names)
    def test_workflow_only_and_unrelated_changes_cannot_publish(self):
        self.assertFalse(self.check(['.github/workflows/sample.yml','README.md']))
    def test_source_change_or_deleted_payload_requests_qualified_publication(self):
        self.assertTrue(self.check(['downloads/sample/removed.txt']))
        self.assertTrue(self.check(['downloads/sample/nested/new.py']))
    def test_pr_and_feature_branch_cannot_publish(self):
        self.assertFalse(self.check(['downloads/sample/new.py'],event='pull_request'))
        self.assertFalse(self.check(['downloads/sample/new.py'],ref='refs/heads/feature'))
    def test_tag_cannot_publish_main_only_package(self):
        self.assertFalse(self.check(['downloads/sample/new.py'],ref='refs/tags/sample-v1'))
    def test_unknown_or_missing_push_base_fails_closed(self):
        for before in ('','0'*40,'not-a-commit'):
            with self.assertRaisesRegex(ValueError,'EXACT_EXISTING_MAIN_BASE_REQUIRED'):self.check([],before=before)
    def test_explicit_main_dispatch_remains_available(self):
        self.assertTrue(self.check([],event='workflow_dispatch'))

if __name__=='__main__':unittest.main()
