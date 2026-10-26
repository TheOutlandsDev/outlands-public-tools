"""Controller and real hidden Tk widgets using fictional state only. MIT."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import profile_gui as gui


class FakeAPI:
    def __init__(self):self.calls=[];self.active=None;self.pending=None;self.allowed=True
    def status(self,workspace):
        self.calls.append(('status',workspace));return {'status':'OK','active_profile':self.active,'pending':self.pending,'profiles':[{'id':'orchard'}],'history':[]}
    def initialize(self,workspace):self.calls.append(('init',workspace));return {'status':'OK'}
    def import_profile(self,workspace,profile,source):self.calls.append(('import',workspace,profile,source));return {'status':'OK'}
    def plan(self,workspace,action,profile=None):self.calls.append(('plan',workspace,action,profile));return {'status':'OK','allowed':self.allowed,'action':action}
    def activate(self,workspace,profile):self.calls.append(('activate',workspace,profile));self.active=profile;return {'status':'OK'}
    def deactivate(self,workspace):self.calls.append(('deactivate',workspace));self.active=None;return {'status':'OK'}
    def recover(self,workspace):self.calls.append(('recover',workspace));self.pending=None;return {'status':'OK','outcome':'recovered'}


class FakeView:
    def __init__(self):self.confirmed=True;self.states=[];self.results=[];self.errors=[];self.prompts=[]
    def get_workspace(self):return '/fictional/workspace'
    def get_source(self):return '/fictional/source'
    def get_profile(self):return 'orchard'
    def confirm(self,title,message):self.prompts.append((title,message));return self.confirmed
    def show_state(self,result):self.states.append(result)
    def show_result(self,result):self.results.append(result)
    def show_error(self,code):self.errors.append(code)


class ControllerTests(unittest.TestCase):
    def setUp(self):self.api=FakeAPI();self.view=FakeView();self.controller=gui.Controller(self.api,self.view)
    def test_construction_is_inert(self):self.assertEqual(self.api.calls,[])
    def test_preview_only_calls_plan(self):
        self.controller.preview();self.assertEqual(self.api.calls,[('plan','/fictional/workspace','activate','orchard')]);self.assertFalse(self.view.prompts)
    def test_activation_previews_confirms_then_revalidates_in_engine(self):
        self.controller.activate();self.assertEqual([r[0] for r in self.api.calls],['plan','activate','status']);self.assertEqual(self.api.active,'orchard');self.assertIn('managed active folder',self.view.prompts[0][1])
    def test_cancelled_activation_has_no_mutation(self):
        self.view.confirmed=False;self.controller.activate();self.assertEqual([r[0] for r in self.api.calls],['plan'])
    def test_denied_plan_has_no_mutation_or_confirmation(self):
        self.api.allowed=False;self.controller.activate();self.assertEqual([r[0] for r in self.api.calls],['plan']);self.assertEqual(self.view.errors,['PLAN_NOT_ALLOWED']);self.assertFalse(self.view.prompts)
    def test_deactivation_uses_plan_without_profile(self):
        self.api.active='orchard';self.controller.deactivate();self.assertEqual(self.api.calls[0],('plan','/fictional/workspace','deactivate',None));self.assertIsNone(self.api.active)
    def test_init_and_import_require_separate_explicit_confirmation(self):
        self.controller.initialize();self.controller.import_profile();self.assertEqual([r[0] for r in self.api.calls],['init','status','import','status']);self.assertEqual(len(self.view.prompts),2)
    def test_cancelled_init_and_import_call_nothing(self):
        self.view.confirmed=False;self.controller.initialize();self.controller.import_profile();self.assertEqual(self.api.calls,[])
    def test_recover_without_pending_is_read_only(self):
        self.controller.recover();self.assertEqual([r[0] for r in self.api.calls],['status']);self.assertEqual(self.view.results[-1]['code'],'NO_PENDING_OPERATION')
    def test_recovery_confirms_and_refreshes(self):
        self.api.pending='fictional-operation';self.controller.recover();self.assertEqual([r[0] for r in self.api.calls],['status','recover','status']);self.assertIsNone(self.api.pending)
    def test_cancelled_recovery_retains_pending(self):
        self.api.pending='fictional-operation';self.view.confirmed=False;self.controller.recover();self.assertEqual([r[0] for r in self.api.calls],['status']);self.assertEqual(self.api.pending,'fictional-operation')
    def test_private_exception_text_is_not_shown(self):
        def fail(_workspace):raise OSError('/fictional/private-file: operation failed')
        self.api.status=fail;self.controller.refresh();self.assertEqual(self.view.errors,['OPERATION_FAILED'])
    def test_fixed_domain_code_is_shown(self):
        def fail(_workspace):raise ValueError('ACTIVE_TREE_MISMATCH')
        self.api.status=fail;self.controller.refresh();self.assertEqual(self.view.errors,['ACTIVE_TREE_MISMATCH'])


class TkWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root=tk.Tk();cls.root.withdraw()
        except Exception:
            if os.environ.get('PROFILE_MANAGER_REQUIRE_TK')=='1':raise RuntimeError('TK_REQUIRED_FOR_GUI_TESTS') from None
            raise unittest.SkipTest('Tk/display unavailable; native widget validation was not run') from None
    @classmethod
    def tearDownClass(cls):cls.root.destroy()
    def setUp(self):
        self.api=FakeAPI();self.view=gui.Desktop(self.root,self.api)
        self.view.confirm=lambda *_:True;self.errors=[];self.view.show_error=self.errors.append
        self.view.workspace.set('/fictional/workspace');self.view.profile.set('orchard');self.view.source.set('/fictional/source')
    def tearDown(self):
        for widget in self.root.winfo_children():widget.destroy()
    def test_native_construction_and_editing_do_not_call_engine(self):
        self.root.update_idletasks();self.assertEqual(self.api.calls,[]);self.assertIn('active',self.view.active_path.get())
    def test_native_workspace_browse_only_selects_existing_without_initializing(self):
        from unittest.mock import patch
        with patch('tkinter.filedialog.askdirectory',return_value='/fictional/existing') as dialog:
            self.view.choose_workspace()
        self.assertTrue(dialog.call_args.kwargs['mustexist']);self.assertIn('existing workspace',dialog.call_args.kwargs['title'])
        self.assertIn('type a new folder path',self.view.workspace_hint.cget('text'))
        self.assertEqual(self.view.workspace.get(),'/fictional/existing');self.assertEqual(self.api.calls,[])
    def test_native_preview_button_is_read_only(self):
        self.view.preview_button.invoke();self.assertEqual([r[0] for r in self.api.calls],['plan']);self.assertIn('Preview allowed: yes',self.view.details.get('1.0','end'));self.assertNotIn('"allowed":',self.view.details.get('1.0','end'))
    def test_native_activation_refreshes_list_and_active_label(self):
        self.view.activate_button.invoke();self.assertEqual(self.api.active,'orchard');self.assertEqual(self.view.profiles.get(0,'end'),('orchard',));self.assertIn('Active: orchard',self.view.summary.get())
    def test_native_profile_selection_sets_id(self):
        self.view.controller.refresh();self.view.profile.set('');self.view.profiles.selection_set(0);self.view.selected_profile();self.assertEqual(self.view.profile.get(),'orchard')
    def test_native_cancelled_action_preserves_state(self):
        self.view.confirm=lambda *_:False;self.view.activate_button.invoke();self.assertIsNone(self.api.active);self.assertEqual([r[0] for r in self.api.calls],['plan'])
    def test_native_recovery_and_deactivation_buttons_are_wired(self):
        self.api.pending='fictional';self.view.recover_button.invoke();self.assertIsNone(self.api.pending)
        self.api.active='orchard';self.view.deactivate_button.invoke();self.assertIsNone(self.api.active)
    def test_native_result_is_literal_text_and_read_only(self):
        self.view.show_result({'status':'OK','note':'<script>fictional</script>'});self.assertNotIn('<script>',self.view.details.get('1.0','end'))
        self.view.details_toggle.invoke();self.assertIn('<script>fictional</script>',self.view.details.get('1.0','end'));self.assertEqual(str(self.view.details.cget('state')),'disabled')
        self.view.details_toggle.invoke();self.assertNotIn('<script>',self.view.details.get('1.0','end'))
    def test_native_retained_preparation_explains_review_without_a_pending_change(self):
        result={'status':'REVIEW_REQUIRED','active_profile':None,'pending':None,'profiles':[],
            'history':[{'id':'a'*32,'action':'preparation','profile':None,'phase':'retained_preparation','outcome':'retained_preparation'}],
            'issues':[{'code':'RETAINED_PREPARATION'}]}
        self.view.show_state(result);text=self.view.details.get('1.0','end')
        self.assertIn('other verified changes can continue',text);self.assertIn('no active change',text)
        self.assertIn('Pending operation: none',text);self.assertNotIn('retained_preparation',text)
        self.assertFalse(self.view.structured.get());self.assertEqual(self.api.calls,[])
        self.view.preview_button.invoke();self.assertEqual([row[0] for row in self.api.calls],['plan'])
    def test_native_widgets_run_real_generated_workspace_flow(self):
        import profile_engine
        from examples.generate import generate
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw).resolve();generate(base/'fixtures')
            self.view.controller=gui.Controller(profile_engine,self.view)
            self.view.workspace.set(str(base/'workspace'));self.view.profile.set('orchard');self.view.source.set(str(base/'fixtures/orchard'))
            self.view.controller.initialize();self.view.controller.import_profile();self.view.controller.preview();self.view.controller.activate()
            self.assertFalse(self.errors);self.assertEqual(profile_engine.status(base/'workspace')['active_profile'],'orchard')
            self.assertIn('Active: orchard',self.view.summary.get());self.assertTrue((base/'workspace/active/config/demo.ini').is_file())
            self.view.controller.deactivate();self.assertIsNone(profile_engine.status(base/'workspace')['active_profile'])
            self.assertTrue((base/'fixtures/orchard/config/demo.ini').is_file());self.assertFalse(self.errors)


if __name__=='__main__':unittest.main()
