"""Original MIT idle-start dashboard; no collection or external requests on construction."""
from __future__ import annotations
import json
import queue
import re
import threading
from monitor_core import MonitorError, demo, export_report, load_replay
from monitor_worker import run_isolated, system_snapshot


class Desktop:
    def __init__(self, root, runner=run_isolated):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.runner = runner
        self.worker = None
        self.stopped = threading.Event()
        self.messages = queue.Queue(maxsize=2)
        self.report = None
        self.after_id = None
        self.closing = False
        self.interface = tk.StringVar()
        self.seconds = tk.StringVar(value='30')
        self.lookup_ip = tk.StringVar()
        self.summary = tk.StringVar(value='Idle · Try fictional data first, or choose an explicit local action.')
        self.system = tk.StringVar(value='System statistics are read only when you request a snapshot.')
        root.title('OUTLANDS Desktop Network Monitor')
        root.geometry('1080x700');root.minsize(850, 560)
        root.rowconfigure(0, weight=1);root.columnconfigure(0, weight=1)
        frame = ttk.Frame(root, padding=16);frame.grid(sticky='nsew')
        frame.columnconfigure(1, weight=1);frame.rowconfigure(6, weight=1)
        ttk.Label(frame, text='Desktop Network Monitor', font=('TkDefaultFont', 18, 'bold')).grid(row=0, column=0, columnspan=4, sticky='w')
        ttk.Label(frame, text='Local rule matches are review hints. Reputation observations are separate; neither proves malware.').grid(row=1, column=0, columnspan=4, sticky='w', pady=10)
        self.demo_button = ttk.Button(frame, text='Fictional demo · no network', command=self.run_demo)
        self.demo_button.grid(row=2, column=0, sticky='ew')
        self.replay_button = ttk.Button(frame, text='Open metadata JSON…', command=self.replay)
        self.replay_button.grid(row=2, column=1, sticky='ew', padx=8)
        self.stats_button = ttk.Button(frame, text='System snapshot · local', command=self.stats)
        self.stats_button.grid(row=2, column=2, columnspan=2, sticky='ew')
        ttk.Label(frame, text='Exact capture interface').grid(row=3, column=0, sticky='w', pady=10)
        ttk.Entry(frame, textvariable=self.interface).grid(row=3, column=1, sticky='ew', padx=8)
        ttk.Entry(frame, textvariable=self.seconds, width=8).grid(row=3, column=2, sticky='ew')
        self.start_button = ttk.Button(frame, text='Start live capture…', command=self.start)
        self.start_button.grid(row=3, column=3, sticky='ew', padx=(8, 0))
        ttk.Label(frame, textvariable=self.system, wraplength=1000).grid(row=4, column=0, columnspan=4, sticky='w', pady=8)
        ttk.Label(frame, textvariable=self.summary, wraplength=1000).grid(row=5, column=0, columnspan=4, sticky='w', pady=8)
        self.events = ttk.Treeview(frame, columns=('packet', 'protocol', 'bytes', 'rules'), show='headings')
        for column, text in [('packet', 'Packet'), ('protocol', 'Protocol'), ('bytes', 'Observed bytes'), ('rules', 'Local review rules')]:
            self.events.heading(column, text=text)
        self.events.grid(row=6, column=0, columnspan=4, sticky='nsew')
        ttk.Label(frame, text='Optional OTX · sends only the IPv4 address you enter after confirmation').grid(row=7, column=0, columnspan=4, sticky='w', pady=(12, 6))
        ttk.Entry(frame, textvariable=self.lookup_ip).grid(row=8, column=0, columnspan=2, sticky='ew')
        self.lookup_button = ttk.Button(frame, text='Send one address to OTX…', command=self.lookup)
        self.lookup_button.grid(row=8, column=2, columnspan=2, sticky='ew', padx=(8, 0))
        bar = ttk.Frame(frame);bar.grid(row=9, column=0, columnspan=4, sticky='ew', pady=12)
        self.stop_button = ttk.Button(bar, text='Stop', command=self.stop, state='disabled');self.stop_button.pack(side='left')
        self.save_button = ttk.Button(bar, text='Save aggregate report…', command=self.save, state='disabled');self.save_button.pack(side='left', padx=10)
        ttk.Label(frame, text='No automatic files, reputation requests or packet capture. Packet payloads are not stored by this app.').grid(row=10, column=0, columnspan=4, sticky='w')
        root.protocol('WM_DELETE_WINDOW', self.close)

    def confirm(self, title, text):
        from tkinter import messagebox
        return messagebox.askyesno(title, text, parent=self.root, default='no')

    def error(self, code):
        from tkinter import messagebox
        messagebox.showerror('Action stopped', code.replace('_', ' ').capitalize(), parent=self.root)

    def busy(self, active):
        for widget in (self.demo_button, self.replay_button, self.stats_button, self.start_button, self.lookup_button):
            widget.configure(state='disabled' if active else 'normal')
        self.stop_button.configure(state='normal' if active else 'disabled')
        self.save_button.configure(state='normal' if not active and self.report is not None else 'disabled')

    def post(self, kind, value):
        try:self.messages.put_nowait((kind, value))
        except queue.Full:
            try:self.messages.get_nowait()
            except queue.Empty:pass
            self.messages.put_nowait((kind, value))

    def launch(self, function):
        if self.worker is not None:return
        self.stopped = threading.Event();self.busy(True)
        def run():
            try:
                kind, value = function();self.post(kind, value)
            except MonitorError as error:
                code = str(error) if re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', str(error)) else 'OPERATION_FAILED'
                self.post('error', code)
            except Exception:self.post('error', 'OPERATION_FAILED')
        self.worker = threading.Thread(target=run, daemon=True);self.worker.start()
        self.after_id = self.root.after(50, self.poll)

    def show(self, report, running=False):
        self.report = report
        self.summary.set(('FICTIONAL DEMO' if report['mode'] == 'demo' else report['mode'].upper()) +
                         f" · {report['packets_observed']} IPv4 packets · {report['packets_matching_local_rules']} matched local rules · " + ('monitoring' if running else report['outcome']) +
                         (' · incomplete capture' if report['capture_incomplete'] else ''))
        self.events.delete(*self.events.get_children())
        for row in report['events']:
            self.events.insert('', 'end', values=(row['packet'], row['protocol'], row['bytes'], ', '.join(row['rules'])))

    def run_demo(self):
        if self.worker is None:self.show(demo().report());self.busy(False)

    def replay(self):
        if self.worker is not None:return
        from tkinter import filedialog
        value = filedialog.askopenfilename(parent=self.root, title='Choose packet-metadata JSON')
        if value:self.launch(lambda: ('report', load_replay(value).report()))

    def stats(self):
        self.launch(lambda: ('system', system_snapshot()))

    def start(self):
        if self.worker is not None:return
        interface = self.interface.get()
        try:
            seconds = float(self.seconds.get())
            if not 1 <= seconds <= 600 or not interface:raise ValueError()
        except ValueError:self.error('CAPTURE_SETTINGS_INVALID');return
        if not self.confirm('Start local packet capture?',
                            'Capture IPv4 metadata on this exact interface:\n'+interface+
                            '\n\nOnly use an interface you are authorized to inspect. No payloads are saved. No addresses are sent to OTX automatically.'):return
        self.report = None
        self.launch(lambda: ('report', self.runner('capture', (interface, seconds), self.stopped,
                                                   on_update=lambda report:self.post('progress', report))))

    def lookup(self):
        if self.worker is not None:return
        value = self.lookup_ip.get()
        if not self.confirm('Send an address to OTX?',
                            'Send this IPv4 address to https://otx.alienvault.com:\n'+value+
                            '\n\nYour OTX_API_KEY environment value is used only for this request. A pulse count is not a malware verdict.'):return
        self.launch(lambda: ('lookup', self.runner('lookup', (value,), self.stopped)))

    def poll(self):
        self.after_id = None
        try:kind, value = self.messages.get_nowait()
        except queue.Empty:kind = None
        if not self.closing:
            if kind in ('report','progress'):self.show(value,running=kind=='progress')
            elif kind == 'system':
                self.system.set(f"CPU {value['cpu_percent']:.1f}% · RAM {value['memory_percent']:.1f}% · Network cumulative totals: {value['network_bytes_received_total']} received / {value['network_bytes_sent_total']} sent bytes")
            elif kind == 'lookup':self.summary.set('OTX observation: '+str(value['reported_pulse_count'])+' reported pulses. This is not a malware verdict.')
            elif kind == 'error':self.summary.set('Stopped: '+value.replace('_', ' ').lower());self.error(value)
        if self.worker is not None and (self.worker.is_alive() or not self.messages.empty()):
            self.after_id = self.root.after(50, self.poll)
        else:
            self.worker = None
            if self.closing:self.root.destroy()
            else:self.busy(False)

    def stop(self):
        self.stopped.set();self.stop_button.configure(state='disabled');self.summary.set('Stopping the owned worker…')

    def save(self):
        if self.worker is not None or self.report is None:return
        from tkinter import filedialog
        value = filedialog.asksaveasfilename(parent=self.root, title='Choose a new aggregate report', defaultextension='.json')
        if value:
            try:export_report(value, self.report)
            except Exception:self.error('SAVE_REFUSED_OR_FAILED')

    def close(self):
        self.closing = True;self.stopped.set()
        if self.worker is None:self.root.destroy()


def main():
    root = None
    try:
        import tkinter as tk
        root = tk.Tk();Desktop(root);root.mainloop();return 0
    except Exception:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'GUI_UNAVAILABLE'}));return 2
    finally:
        if root is not None:
            try:root.destroy()
            except Exception:pass
