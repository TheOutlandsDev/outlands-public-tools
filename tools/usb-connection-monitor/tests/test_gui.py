"""Real withdrawn Tk widgets, generated observations, no live Windows query."""
from pathlib import Path
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import usb_core as core
import usb_gui as gui
from inspection_support import TextError
DEVICE = 'USB\\FICTIONAL\\DEMO_ONLY'


class WidgetTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk();self.root.withdraw()
        except Exception:
            if os.environ.get('USB_MONITOR_REQUIRE_TK') == '1':raise
            self.skipTest('Native Tk/display unavailable')
        self.addCleanup(self.cleanup)
        self.query = Mock(return_value=[{'id': DEVICE, 'name': 'Fictional camera'}])
        self.view = gui.Desktop(self.root, query=self.query)
        self.view.error = Mock()
        self.root.update()

    def cleanup(self):
        try:
            self.view.stop.set()
            if self.view.worker is not None:self.view.worker.join(timeout=3)
            if self.view.after_id is not None:self.root.after_cancel(self.view.after_id)
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:pass

    def pump(self, predicate, timeout=4):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('Widget workflow timed out')

    def scan(self):
        self.view.scan_button.invoke()
        self.pump(lambda:self.view.worker is None)

    def test_construction_is_idle_without_collection(self):
        self.query.assert_not_called();self.assertIsNone(self.view.worker)
        self.assertEqual(self.view.device_choice.current(), -1)
        self.assertTrue(self.view.stop_button.instate(['disabled']))

    def test_demo_runs_actual_core_without_query(self):
        self.view.demo_button.invoke()
        self.query.assert_not_called()
        self.assertIn('FICTIONAL DEMO', self.view.summary.get())
        self.assertEqual(len(self.view.timeline.get_children()), 3)
        self.assertTrue(self.view.save_button.instate(['!disabled']))

    def test_gap_demo_explains_unknown_not_disconnection(self):
        self.view.scenario.set('query-gap');self.view.demo_button.invoke()
        values = str([self.view.timeline.item(item)['values'] for item in self.view.timeline.get_children()])
        self.assertIn('unknown', values);self.assertIn('resumed', values)
        self.assertNotIn('Presence changed to absent', values)

    def test_scan_is_explicit_and_does_not_select_for_user(self):
        self.scan();self.query.assert_called_once()
        self.assertEqual(self.view.device_choice.current(), -1)
        self.assertEqual(len(self.view.devices), 1)
        self.assertIn('Fictional camera', self.view.device_choice['values'][0])

    def test_start_without_selection_does_not_query(self):
        self.view.start_button.invoke();self.query.assert_not_called()
        self.view.error.assert_called_once_with('SELECT_AN_ENTRY_FIRST')

    def test_invalid_settings_refuse_before_starting_worker(self):
        self.scan();self.view.device_choice.current(0);self.view.seconds.set('nan')
        self.view.start_button.invoke()
        self.assertIsNone(self.view.worker);self.assertEqual(self.query.call_count, 1)
        self.view.error.assert_called_once_with('SETTINGS_INVALID')

    def test_live_worker_uses_real_engine_with_generated_query(self):
        self.scan();self.view.device_choice.current(0)
        self.view.seconds.set('1');self.view.interval.set('.5')
        self.view.start_button.invoke()
        self.assertTrue(self.view.start_button.instate(['disabled']))
        self.pump(lambda:self.view.worker is None)
        self.assertEqual(self.view.report['mode'], 'live')
        self.assertGreater(self.view.report['sample_counts']['present'], 0)
        self.assertNotIn(DEVICE, json.dumps(self.view.report))
        self.assertNotIn('Fictional camera', json.dumps(self.view.report))

    def test_stop_cancels_worker_without_extra_query(self):
        self.scan();self.view.device_choice.current(0)
        self.view.seconds.set('30');self.view.start_button.invoke()
        self.view.stop_button.invoke();self.pump(lambda:self.view.worker is None)
        self.assertEqual(self.view.report['outcome'], 'cancelled')
        self.assertTrue(self.view.stop_button.instate(['disabled']))

    def test_unknown_errors_do_not_show_private_exception_text(self):
        self.query.side_effect = RuntimeError('fictional private error details')
        self.scan()
        self.view.error.assert_called_once_with('OPERATION_FAILED')
        self.assertNotIn('fictional private', self.view.summary.get())

    def test_save_explicit_new_report_has_no_device_metadata(self):
        self.view.demo_button.invoke()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(path)):
                self.view.save_button.invoke()
            result = json.loads(path.read_text());self.assertEqual(result, core.demo())
            self.assertNotIn(DEVICE, path.read_text())

    def test_selected_id_requires_explicit_details_action(self):
        self.scan();self.view.device_choice.current(0)
        with patch('tkinter.messagebox.showinfo') as details:
            self.view.identity_button.invoke()
        self.assertEqual(details.call_args.args[1], DEVICE)
        self.assertNotIn(DEVICE, self.view.summary.get())

    def test_demo_does_not_save_automatically(self):
        with patch.object(gui, 'export_report') as save:
            self.view.demo_button.invoke()
        save.assert_not_called()

    def test_close_cancels_current_worker_before_destroying_window(self):
        self.scan();self.view.device_choice.current(0)
        self.view.seconds.set('30');self.view.start_button.invoke()
        worker = self.view.worker
        self.view.close()
        end = time.monotonic()+4
        while self.view.worker is not None and time.monotonic()<end:
            try:self.root.update()
            except Exception:break
            time.sleep(.01)
        self.assertFalse(worker.is_alive())
        self.assertIsNone(self.view.worker)
        self.assertTrue(self.view.closing)


if __name__ == '__main__':unittest.main()
