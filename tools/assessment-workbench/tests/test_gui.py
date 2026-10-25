"""Real Tk widgets over new disposable stores, with all dialogs intercepted."""

import copy
import json
import os
import unittest
from unittest.mock import patch

from test_core import StoreFixture, core, one_submission


try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None

if tk is not None:
    import workbench_gui as gui


class WorkbenchGuiTests(StoreFixture):
    @classmethod
    def setUpClass(cls):
        required = os.environ.get("ASSESSMENT_WORKBENCH_REQUIRE_TK") == "1"
        if tk is None:
            if required:
                raise AssertionError("TK_REQUIRED_UNAVAILABLE")
            raise unittest.SkipTest("Tk is unavailable")
        try:
            probe = tk.Tk()
            probe.withdraw()
            probe.update_idletasks()
            probe.destroy()
        except tk.TclError:
            if required:
                raise AssertionError("TK_DISPLAY_REQUIRED_UNAVAILABLE") from None
            raise unittest.SkipTest("Tk display is unavailable") from None

    def setUp(self):
        super().setUp()
        self.showerror = self.start_patch("showerror")
        self.showinfo = self.start_patch("showinfo")
        self.confirm = self.start_patch("askyesno", return_value=True)
        self.root = tk.Tk()
        self.root.withdraw()

        def destroy():
            try:
                self.root.destroy()
            except tk.TclError:
                pass

        self.addCleanup(destroy)
        self.app = gui.WorkbenchApp(self.root)
        self.root.update_idletasks()

    def start_patch(self, name, **kwargs):
        patcher = patch.object(gui.messagebox, name, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def open_empty(self):
        snapshot = core.create_store(self.path)
        self.app.set_snapshot(self.path, snapshot)
        return snapshot

    def apply_submission_form(self, identifier="fictional_original", revision="1"):
        self.app.forms["submission"]["id"].set(identifier)
        self.app.forms["submission"]["series_id"].set("fictional_series")
        self.app.forms["submission"]["revision"].set(revision)
        self.app.buttons["submission_apply"].invoke()

    def linked_records(self):
        data = one_submission()
        data["submissions"].append(
            {
                "id": "fictional_replacement",
                "series_id": "fictional_series",
                "revision": 2,
            }
        )
        data["findings"] = [
            {
                "id": "fictional_finding",
                "submission_id": "fictional_original",
                "state": "open",
                "selected_retest_id": None,
            }
        ]
        data["retests"] = [
            {
                "id": "fictional_retest",
                "finding_id": "fictional_finding",
                "submission_id": "fictional_replacement",
                "outcome": "not_run",
            }
        ]
        return data

    def test_startup_is_empty_and_does_not_create_a_private_store(self):
        self.assertIsNone(self.app.store_path)
        self.assertEqual(self.app.revision, 0)
        self.assertEqual(self.app.draft, core.empty_records())
        self.assertIs(self.app.dirty, False)
        self.assertEqual(list(self.parent.iterdir()), [])
        for kind in ("submission", "finding", "retest"):
            self.assertIsInstance(self.app.tables[kind], ttk.Treeview)
            self.assertEqual(self.app.tables[kind].get_children(), ())
        self.assertIn("REVIEW_REQUIRED", self.app.status_var.get())

    def test_real_apply_and_save_buttons_keep_edits_in_memory_until_commit(self):
        initial = self.open_empty()
        self.apply_submission_form()
        self.assertEqual(self.app.draft, one_submission())
        self.assertTrue(self.app.dirty)
        self.assertEqual(
            self.app.tables["submission"].get_children(), ("fictional_original",)
        )
        self.assertEqual(core.load_store(self.path), initial)
        self.app.buttons["save"].invoke()
        saved = core.load_store(self.path)
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["records"], one_submission())
        self.assertFalse(self.app.dirty)
        self.assertEqual(self.app.revision, 1)
        self.showerror.assert_not_called()

    def test_reference_state_and_outcome_controls_are_readonly_comboboxes(self):
        self.open_empty()
        data = self.linked_records()
        for row in data["submissions"]:
            self.assertTrue(self.app.apply_record("submission", row))
        self.assertTrue(self.app.apply_record("finding", data["findings"][0]))
        self.assertTrue(self.app.apply_record("retest", data["retests"][0]))
        for kind, names in (
            ("finding", ("submission_id", "selected_retest_id", "state")),
            ("retest", ("finding_id", "submission_id", "outcome")),
        ):
            for name in names:
                widget = self.app.form_widgets[kind][name]
                self.assertIsInstance(widget, ttk.Combobox)
                self.assertEqual(str(widget.cget("state")), "readonly")
        self.assertEqual(
            set(self.app.form_widgets["finding"]["submission_id"].cget("values")),
            {"fictional_original", "fictional_replacement"},
        )
        self.assertIn(
            "fictional_finding",
            self.app.form_widgets["retest"]["finding_id"].cget("values"),
        )
        self.assertIn(
            "fictional_retest",
            self.app.form_widgets["finding"]["selected_retest_id"].cget("values"),
        )
        self.assertIn(
            "(none)",
            self.app.form_widgets["finding"]["selected_retest_id"].cget("values"),
        )
        self.assertEqual(
            set(self.app.form_widgets["finding"]["state"].cget("values")),
            {"open", "retest_pending", "closure_claimed"},
        )
        self.assertEqual(
            set(self.app.form_widgets["retest"]["outcome"].cget("values")),
            {"not_run", "still_present", "not_observed", "inconclusive"},
        )

    def test_none_sentinel_is_applied_as_json_null_without_silent_selection(self):
        self.open_empty()
        self.apply_submission_form()
        values = {
            "id": "fictional_finding",
            "submission_id": "fictional_original",
            "state": "open",
            "selected_retest_id": "(none)",
        }
        for name, value in values.items():
            self.app.forms["finding"][name].set(value)
        self.app.buttons["finding_apply"].invoke()
        self.assertIs(self.app.draft["findings"][0]["selected_retest_id"], None)
        self.assertEqual(self.app.draft["findings"][0]["state"], "open")
        self.assertEqual(
            self.app.validate_draft()["status"], "DECLARED_RECORDS_CONSISTENT"
        )

    def test_selection_populates_real_form_and_record_ids_remain_immutable(self):
        self.open_empty()
        self.apply_submission_form()
        self.assertTrue(self.app.select_record("submission", "fictional_original"))
        self.assertEqual(self.app.forms["submission"]["revision"].get(), "1")
        self.assertEqual(
            str(self.app.form_widgets["submission"]["id"].cget("state")), "readonly"
        )
        before = copy.deepcopy(self.app.draft)
        changed = {**before["submissions"][0], "id": "changed_id"}
        self.assertFalse(
            self.app.apply_record("submission", changed, old_id="fictional_original")
        )
        self.assertEqual(self.app.draft, before)
        self.assertIn("RECORD_ID_IMMUTABLE", str(self.showerror.call_args))

    def test_duplicate_or_schema_invalid_record_does_not_mutate_draft_or_echo_values(
        self,
    ):
        self.open_empty()
        self.apply_submission_form()
        before = copy.deepcopy(self.app.draft)
        self.assertFalse(self.app.apply_record("submission", before["submissions"][0]))
        self.assertEqual(self.app.draft, before)
        canary = "fictional-sensitive-narrative-canary"
        bad = {**before["submissions"][0], "id": "another", "narrative": canary}
        self.assertFalse(self.app.apply_record("submission", bad))
        self.assertEqual(self.app.draft, before)
        self.assertNotIn(canary, str(self.showerror.call_args))

    def test_unapplied_form_text_blocks_save_until_applied_or_explicitly_cleared(self):
        initial = self.open_empty()
        self.app.forms["submission"]["id"].set("unapplied_fictional")
        self.app.buttons["save"].invoke()
        self.assertEqual(core.load_store(self.path), initial)
        self.assertEqual(self.app.draft, core.empty_records())
        self.assertIn("UNAPPLIED_FORM_CHANGES", str(self.showerror.call_args))
        self.app.buttons["submission_clear"].invoke()
        self.assertEqual(self.app.form_dirty, set())
        self.assertEqual(self.app.forms["submission"]["id"].get(), "")
        self.assertEqual(core.load_store(self.path), initial)

    def test_remove_keeps_dependent_records_and_persists_a_review_draft(self):
        core.create_store(self.path)
        data = self.linked_records()
        snapshot = core.save_records(self.path, data, expected_revision=0)
        self.app.set_snapshot(self.path, snapshot)
        self.assertTrue(self.app.select_record("submission", "fictional_original"))
        self.app.buttons["submission_remove"].invoke()
        self.assertEqual(
            [row["id"] for row in self.app.draft["submissions"]],
            ["fictional_replacement"],
        )
        self.assertEqual(self.app.draft["findings"], data["findings"])
        self.assertEqual(self.app.draft["retests"], data["retests"])
        self.assertEqual(self.app.validate_draft()["status"], "REVIEW_REQUIRED")
        saved = self.app.save_draft()
        self.assertIsNotNone(saved)
        self.assertEqual(saved["records"]["findings"], data["findings"])
        self.assertEqual(saved["records"]["retests"], data["retests"])
        self.assertEqual(core.load_store(self.path)["revision"], 2)

    def test_validate_button_does_not_commit_or_modify_selected_store(self):
        initial = self.open_empty()
        self.apply_submission_form()
        before = copy.deepcopy(self.app.draft)
        self.app.buttons["validate"].invoke()
        self.assertEqual(core.load_store(self.path), initial)
        self.assertEqual(self.app.draft, before)
        self.assertTrue(self.app.dirty)
        self.assertIn("DECLARED_RECORDS_CONSISTENT", self.app.status_var.get())

    def test_stale_save_preserves_unsaved_draft_and_does_not_overwrite_newer_data(self):
        self.open_empty()
        self.apply_submission_form()
        draft = copy.deepcopy(self.app.draft)
        external = one_submission()
        external["submissions"][0]["id"] = "fictional_external"
        committed = core.save_records(self.path, external, expected_revision=0)
        self.assertIsNone(self.app.save_draft())
        self.assertEqual(self.app.draft, draft)
        self.assertEqual(self.app.revision, 0)
        self.assertTrue(self.app.dirty)
        self.assertEqual(core.load_store(self.path), committed)
        self.assertTrue(self.showerror.called)
        self.assertNotIn(str(self.path), str(self.showerror.call_args))

    def test_history_preview_and_clone_keep_the_original_source_after_store_switch(
        self,
    ):
        core.create_store(self.path)
        original = core.save_records(self.path, one_submission(), expected_revision=0)
        self.app.set_snapshot(self.path, original)
        self.app.buttons["history"].invoke()
        windows = [
            child
            for child in self.root.winfo_children()
            if isinstance(child, tk.Toplevel)
        ]
        self.assertEqual(len(windows), 1)
        window = windows[0]
        window.withdraw()

        def descendants(widget):
            result = []
            for child in widget.winfo_children():
                result.append(child)
                result.extend(descendants(child))
            return result

        widgets = descendants(window)
        history_table = next(
            widget for widget in widgets if isinstance(widget, ttk.Treeview)
        )
        preview = next(widget for widget in widgets if isinstance(widget, tk.Text))
        clone_button = next(
            widget
            for widget in widgets
            if isinstance(widget, ttk.Button)
            and str(widget.cget("text")).startswith("Clone selected history")
        )
        self.assertEqual(history_table.get_children(), ("0", "1"))
        other_path = self.parent / "fictional-other-store.db"
        core.create_store(other_path)
        other_records = one_submission(9)
        other_records["submissions"][0]["id"] = "fictional_other_store"
        other = core.save_records(other_path, other_records, expected_revision=0)
        self.app.set_snapshot(other_path, other)
        history_table.selection_set("1")
        history_table.event_generate("<<TreeviewSelect>>")
        self.root.update()
        self.assertEqual(json.loads(preview.get("1.0", "end")), original["records"])
        self.assertEqual(str(preview.cget("state")), "disabled")
        clone_path = self.parent / "fictional-history-clone.db"
        with patch.object(
            gui.filedialog, "asksaveasfilename", return_value=str(clone_path)
        ):
            clone_button.invoke()
        self.assertEqual(core.load_store(clone_path), original)
        self.assertEqual(self.app.store_path, other_path)
        self.assertEqual(self.app.draft, other_records)
        self.assertEqual(core.load_store(other_path), other)
        self.showerror.assert_not_called()

    def test_refresh_requires_discard_confirmation_and_cancel_preserves_draft(self):
        initial = self.open_empty()
        self.apply_submission_form()
        draft = copy.deepcopy(self.app.draft)
        self.confirm.return_value = False
        self.assertIsNone(self.app.refresh())
        self.assertEqual(self.app.draft, draft)
        self.assertTrue(self.app.dirty)
        self.confirm.return_value = True
        refreshed = self.app.refresh()
        self.assertEqual(refreshed, initial)
        self.assertEqual(self.app.draft, core.empty_records())
        self.assertFalse(self.app.dirty)


if __name__ == "__main__":
    unittest.main()
