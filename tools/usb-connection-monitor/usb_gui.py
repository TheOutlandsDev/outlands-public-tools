"""Original MIT idle-start desktop; worker threads never touch Tk widgets."""
from __future__ import annotations
import json
import queue
import threading
from usb_core import Settings, demo, export_report, monitor
from usb_windows import query_devices
from inspection_support import TextError

LABELS = {
    'initial_present': 'Initially observed present',
    'initial_absent': 'Initially observed absent',
    'disconnected_observed': 'Presence changed to absent',
    'reconnected_observed': 'Presence changed to present',
    'observation_unavailable': 'Query unavailable — presence unknown',
    'observation_resumed_present': 'Query resumed — observed present',
    'observation_resumed_absent': 'Query resumed — observed absent',
}


class Desktop:
    def __init__(self, root, query=query_devices, runner=monitor):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.query = query
        self.runner = runner
        self.devices = []
        self.report = None
        self.worker = None
        self.stop = threading.Event()
        self.messages = queue.Queue(maxsize=1)
        self.closing = False
        self.after_id = None
        self.selection = tk.StringVar()
        self.seconds = tk.StringVar(value='60')
        self.interval = tk.StringVar(value='2')
        self.scenario = tk.StringVar(value='reconnect')
        self.summary = tk.StringVar(value='Idle. Try a fictional demo, or explicitly scan for USB entries.')
        root.title('OUTLANDS USB Connection Monitor')
        root.geometry('1040x700')
        root.minsize(800, 580)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame = ttk.Frame(root, padding=16)
        frame.grid(sticky='nsew')
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)
        ttk.Label(frame, text='USB Connection Monitor', font=('TkDefaultFont', 18, 'bold')).grid(row=0, column=0, columnspan=4, sticky='w')
        ttk.Label(frame, text='Observe sampled presence. Query gaps stay unknown; short disconnects can be missed.', wraplength=980).grid(row=1, column=0, columnspan=4, sticky='w', pady=(6, 16))
        ttk.Label(frame, text='Fictional demo').grid(row=2, column=0, sticky='w')
        self.demo_choice = ttk.Combobox(frame, textvariable=self.scenario, values=list(('stable', 'reconnect', 'query-gap')), state='readonly')
        self.demo_choice.grid(row=2, column=1, sticky='ew', padx=8)
        self.demo_button = ttk.Button(frame, text='Run demo · no hardware', command=self.run_demo)
        self.demo_button.grid(row=2, column=2, columnspan=2, sticky='ew')
        ttk.Label(frame, text='Windows USB entry').grid(row=3, column=0, sticky='w', pady=12)
        self.device_choice = ttk.Combobox(frame, textvariable=self.selection, state='readonly')
        self.device_choice.grid(row=3, column=1, sticky='ew', padx=8)
        self.scan_button = ttk.Button(frame, text='Scan present entries', command=self.scan)
        self.scan_button.grid(row=3, column=2, sticky='ew')
        self.identity_button = ttk.Button(frame, text='Show selected ID…', command=self.show_identity)
        self.identity_button.grid(row=3, column=3, sticky='ew', padx=(8, 0))
        ttk.Label(frame, text='Duration / interval (seconds)').grid(row=4, column=0, sticky='w')
        timing = ttk.Frame(frame)
        timing.grid(row=4, column=1, sticky='w', padx=8)
        self.duration_entry = ttk.Entry(timing, textvariable=self.seconds, width=10)
        self.duration_entry.pack(side='left')
        self.interval_entry = ttk.Entry(timing, textvariable=self.interval, width=10)
        self.interval_entry.pack(side='left', padx=10)
        self.start_button = ttk.Button(frame, text='Start selected · live', command=self.start)
        self.start_button.grid(row=4, column=2, sticky='ew')
        self.stop_button = ttk.Button(frame, text='Stop', command=self.request_stop, state='disabled')
        self.stop_button.grid(row=4, column=3, sticky='ew', padx=(8, 0))
        ttk.Label(frame, text='Device labels stay local. Reports omit names, instance IDs, machine details and clock dates.', wraplength=980).grid(row=5, column=0, columnspan=4, sticky='w', pady=10)
        ttk.Label(frame, textvariable=self.summary, wraplength=980).grid(row=6, column=0, columnspan=4, sticky='w', pady=8)
        self.timeline = ttk.Treeview(frame, columns=('time', 'event'), show='headings', selectmode='none')
        self.timeline.heading('time', text='Elapsed seconds')
        self.timeline.heading('event', text='Observation')
        self.timeline.column('time', width=140, stretch=False)
        self.timeline.column('event', width=620)
        self.timeline.grid(row=7, column=0, columnspan=4, sticky='nsew')
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.timeline.yview)
        scrollbar.grid(row=7, column=4, sticky='ns')
        self.timeline.configure(yscrollcommand=scrollbar.set)
        self.save_button = ttk.Button(frame, text='Save report as new JSON…', command=self.save, state='disabled')
        self.save_button.grid(row=8, column=0, columnspan=2, sticky='w', pady=12)
        ttk.Label(frame, text='Nothing is saved automatically. No camera/audio capture, device resets, driver changes or uploads.', wraplength=980).grid(row=9, column=0, columnspan=4, sticky='w')
        root.protocol('WM_DELETE_WINDOW', self.close)

    def error(self, code):
        from tkinter import messagebox
        messagebox.showerror('Action stopped', code.replace('_', ' ').capitalize() + '. Read the guide for supported inputs and limits.', parent=self.root)

    def busy(self, value):
        for widget in [self.scan_button, self.identity_button, self.demo_button, self.start_button, self.duration_entry, self.interval_entry]:
            widget.configure(state='disabled' if value else 'normal')
        self.device_choice.configure(state='disabled' if value else 'readonly')
        self.demo_choice.configure(state='disabled' if value else 'readonly')
        self.stop_button.configure(state='normal' if value else 'disabled')
        self.save_button.configure(state='disabled' if value or self.report is None else 'normal')

    def post(self, kind, value):
        try:
            self.messages.put_nowait((kind, value))
        except queue.Full:
            try:
                self.messages.get_nowait()
            except queue.Empty:
                pass
            self.messages.put_nowait((kind, value))

    def launch(self, function):
        if self.worker is not None:
            return
        self.stop = threading.Event()
        self.busy(True)
        def run():
            try:
                kind, value = function()
                self.post(kind, value)
            except Exception as error:
                allowed = {'WINDOWS_REQUIRED', 'POWERSHELL_UNAVAILABLE', 'QUERY_TIMEOUT', 'QUERY_FAILED',
                           'QUERY_OUTPUT_LIMIT', 'QUERY_INVALID', 'CANCELLED'}
                self.post('error', str(error) if isinstance(error, TextError) and str(error) in allowed else 'OPERATION_FAILED')
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()
        self.after_id = self.root.after(50, self.poll)

    def scan(self):
        if self.worker is not None:
            return
        self.summary.set('Reading present Windows USB entries…')
        self.launch(lambda: ('devices', self.query(stop=self.stop)))

    def start(self):
        if self.worker is not None:
            return
        index = self.device_choice.current()
        if not 0 <= index < len(self.devices):
            self.error('SELECT_AN_ENTRY_FIRST')
            return
        try:
            settings = Settings(float(self.seconds.get()), float(self.interval.get())).validate()
        except (TextError, ValueError):
            self.error('SETTINGS_INVALID')
            return
        identity = self.devices[index]['id']
        self.report = None
        self.timeline.delete(*self.timeline.get_children())
        self.summary.set('Live monitoring started. Only the selected PnP instance is tracked.')
        self.launch(lambda: ('report', self.runner(identity, settings, self.query, stop=self.stop,
                                                   on_update=lambda value: self.post('update', value))))

    def show_identity(self):
        if self.worker is not None:
            return
        index = self.device_choice.current()
        if not 0 <= index < len(self.devices):
            self.error('SELECT_AN_ENTRY_FIRST')
            return
        from tkinter import messagebox
        messagebox.showinfo('Private selected instance — do not post', self.devices[index]['id'], parent=self.root)

    def run_demo(self):
        if self.worker is None:
            self.show_report(demo(self.scenario.get()))
            self.busy(False)

    def show_report(self, report, running=False):
        self.report = report
        counts = report['sample_counts']
        self.summary.set(('FICTIONAL DEMO' if report['mode'] == 'demo' else report['mode'].upper()) +
                         ' · ' + ('monitoring' if running else report['outcome'].replace('_', ' ')) + ' · ' + report['status'].replace('_', ' ').lower() +
                         ' · Samples: ' + str(counts['present']) + ' present, ' + str(counts['absent']) +
                         ' absent, ' + str(counts['unknown']) + ' unknown')
        self.timeline.delete(*self.timeline.get_children())
        for event in report['events']:
            self.timeline.insert('', 'end', values=(f"{event['elapsed_ms'] / 1000:.3f}", LABELS[event['kind']]))

    def poll(self):
        self.after_id = None
        try:
            kind, value = self.messages.get_nowait()
        except queue.Empty:
            kind = None
        if not self.closing:
            if kind == 'devices':
                self.devices = value
                self.selection.set('')
                self.device_choice.configure(values=[f"{index + 1}. {row['name']}" for index, row in enumerate(value)])
                self.summary.set(str(len(value)) + ' present USB entries. Choose one explicitly, then start.')
            elif kind in ('report', 'update'):
                self.show_report(value, running=kind == 'update')
            elif kind == 'error':
                self.summary.set('Stopped: ' + value.replace('_', ' ').lower())
                if value != 'CANCELLED':
                    self.error(value)
        if self.worker is not None and (self.worker.is_alive() or not self.messages.empty()):
            self.after_id = self.root.after(50, self.poll)
        else:
            self.worker = None
            if self.closing:
                self.root.destroy()
            else:
                self.busy(False)

    def save(self):
        if self.worker is not None or self.report is None:
            return
        from tkinter import filedialog
        value = filedialog.asksaveasfilename(parent=self.root, title='Choose a new private JSON file',
                                           defaultextension='.json', filetypes=[('JSON report', '*.json')])
        if value:
            try:
                export_report(value, self.report)
                self.summary.set('Report saved to the selected private file.')
            except (TextError, OSError, ValueError):
                self.error('SAVE_REFUSED_OR_FAILED')

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.stop.set()
        if self.worker is None:
            self.root.destroy()
        else:
            self.summary.set('Stopping the current query before closing…')

    def request_stop(self):
        if self.worker is not None:
            self.stop.set()
            self.stop_button.configure(state='disabled')
            self.summary.set('Stopping the current query…')


def main():
    root = None
    try:
        import tkinter as tk
        root = tk.Tk()
        Desktop(root)
        root.mainloop()
        return 0
    except Exception:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'GUI_UNAVAILABLE'}))
        return 2
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == '__main__':
    raise SystemExit(main())
