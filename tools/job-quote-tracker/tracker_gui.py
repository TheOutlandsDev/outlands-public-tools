"""Tk desktop editor. All durable writes go through the versioned Store API."""
from __future__ import annotations
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import tracker as core


class App:
    def __init__(self, root, store=None):
        self.root=root; self.store=store; self.selected=None; self.loaded=None
        self.loading=False; self.dirty=False; self.worker=None; self.cancel=threading.Event()
        self.messages=queue.Queue(); self.closed=False; self.poll_id=None
        root.title('OUTLANDS | Job & Quote Tracker'); root.geometry('1160x820'); root.minsize(920,680)
        root.protocol('WM_DELETE_WINDOW',self.close)
        outer=ttk.Frame(root,padding=16); outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Job & Quote Tracker',font=('Segoe UI',22,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Private local records • explicit saves • revision history • verified recovery').pack(anchor='w',pady=(0,12))
        bar=ttk.Frame(outer);bar.pack(fill='x')
        for title,fn in [('Create store',self.create),('Open store',self.open),('Fictional demo',self.demo),('Restore backup',self.restore),('New job',self.new),('Backup',self.backup),('Export report',self.export)]:
            ttk.Button(bar,text=title,command=fn).pack(side='left',padx=(0,5))
        self.location=tk.StringVar(value='No store selected. Create, open, or try fictional demo data.')
        ttk.Label(outer,textvariable=self.location,wraplength=1080).pack(anchor='w',pady=8)
        filters=ttk.Frame(outer);filters.pack(fill='x',pady=(0,6))
        self.filter=tk.StringVar(value='all'); self.due=tk.StringVar()
        ttk.Label(filters,text='Status').pack(side='left')
        ttk.Combobox(filters,textvariable=self.filter,values=('all',)+core.STATES,state='readonly',width=16).pack(side='left',padx=6)
        ttk.Label(filters,text='Follow-up on/before (YYYY-MM-DD)').pack(side='left')
        ttk.Entry(filters,textvariable=self.due,width=14).pack(side='left',padx=6)
        ttk.Button(filters,text='Refresh / filter',command=lambda:self.run(self.refresh)).pack(side='left')
        columns=('title','customer','status','follow_up','version')
        self.tree=ttk.Treeview(outer,columns=columns,show='headings',height=6,selectmode='browse')
        for column in columns:
            self.tree.heading(column,text=column.replace('_',' ').title());self.tree.column(column,width=190 if column in ('title','customer') else 110)
        self.tree.pack(fill='x');self.tree.bind('<<TreeviewSelect>>',self.select)
        self.book=ttk.Notebook(outer);self.book.pack(fill='both',expand=True,pady=10)
        details=ttk.Frame(self.book,padding=10);quote=ttk.Frame(self.book,padding=10);workflow=ttk.Frame(self.book,padding=10);history=ttk.Frame(self.book,padding=10)
        for frame,title in [(details,'Job details'),(quote,'New quote revision'),(workflow,'Decision & progress'),(history,'Read-only history')]:self.book.add(frame,text=title)
        self.values={}
        for row,(name,label) in enumerate([('title','Job title *'),('customer','Customer / organization *'),('contact','Contact (optional)'),('follow_up','Follow-up date (optional, YYYY-MM-DD)')]):
            ttk.Label(details,text=label).grid(row=row,column=0,sticky='w',pady=4)
            var=tk.StringVar();self.values[name]=var;var.trace_add('write',self.mark)
            ttk.Entry(details,textvariable=var,width=72).grid(row=row,column=1,sticky='ew',padx=10)
        ttk.Label(details,text='Private notes').grid(row=4,column=0,sticky='nw')
        self.notes=tk.Text(details,height=4,width=70,wrap='word');self.notes.grid(row=4,column=1,sticky='nsew',padx=10)
        self.notes.bind('<<Modified>>',self.notes_changed);details.columnconfigure(1,weight=1)
        ttk.Button(details,text='Save job details',command=self.save).grid(row=5,column=1,sticky='w',padx=10,pady=8)
        self.amount=tk.StringVar(value='0.00');self.currency=tk.StringVar(value='USD')
        ttk.Label(quote,text='Saving a revision returns the job to quoted and clears its previous approval and schedule.').pack(anchor='w')
        row=ttk.Frame(quote);row.pack(fill='x',pady=8)
        ttk.Label(row,text='Amount (exactly 2 decimals)').pack(side='left');ttk.Entry(row,textvariable=self.amount,width=18).pack(side='left',padx=8)
        ttk.Combobox(row,textvariable=self.currency,values=sorted(core.CURRENCIES),state='readonly',width=8).pack(side='left')
        ttk.Label(quote,text='Scope *').pack(anchor='w');self.scope=tk.Text(quote,height=3,wrap='word');self.scope.pack(fill='x')
        ttk.Label(quote,text='Exclusions').pack(anchor='w');self.exclusions=tk.Text(quote,height=2,wrap='word');self.exclusions.pack(fill='x')
        ttk.Button(quote,text='Save new quote revision',command=self.quote).pack(anchor='w',pady=8)
        ttk.Label(workflow,text='Decisions are your records of outside approval or rejection. This app does not verify signatures or authority.',wraplength=1000).pack(anchor='w')
        ttk.Label(workflow,text='Decision reference (required; e.g. your record of an email or signed document)').pack(anchor='w',pady=(10,3))
        self.reference=tk.StringVar();ttk.Entry(workflow,textvariable=self.reference,width=100).pack(fill='x')
        row=ttk.Frame(workflow);row.pack(fill='x',pady=8)
        ttk.Button(row,text='Record approval',command=lambda:self.decision('approved')).pack(side='left')
        ttk.Button(row,text='Record rejection',command=lambda:self.decision('rejected')).pack(side='left',padx=8)
        row=ttk.Frame(workflow);row.pack(fill='x',pady=12)
        self.state=tk.StringVar(value='scheduled');self.appointment=tk.StringVar()
        ttk.Label(row,text='Next status').pack(side='left')
        ttk.Combobox(row,textvariable=self.state,values=core.STATES,state='readonly',width=16).pack(side='left',padx=6)
        ttk.Label(row,text='Schedule date').pack(side='left');ttk.Entry(row,textvariable=self.appointment,width=14).pack(side='left',padx=6)
        ttk.Button(row,text='Record status',command=self.status).pack(side='left')
        ttk.Label(workflow,text='Workflow: new → quote → record approval → schedule → in progress → complete → archive.\nCancel an active job before archiving. Follow-up dates are filters, not automatic reminders.').pack(anchor='w')
        self.history=tk.Text(history,wrap='word',state='disabled',height=12);self.history.pack(fill='both',expand=True)
        footer=ttk.Frame(outer);footer.pack(fill='x');self.notice=tk.StringVar(value='Ready. No automatic network access or customer messages.')
        ttk.Label(footer,textvariable=self.notice,wraplength=950).pack(side='left')
        ttk.Button(footer,text='Cancel background task',command=self.cancel.set).pack(side='right')
        if store:self.refresh()
        self.poll_id=root.after(80,self.poll)

    def mark(self,*_):
        if not self.loading:self.dirty=True
    def notes_changed(self,*_):
        if self.notes.edit_modified():self.mark();self.notes.edit_modified(False)
    def okay(self):
        if self.worker and self.worker.is_alive():
            self.notice.set('Wait for the background operation or cancel it first.');return False
        if self.dirty and not messagebox.askyesno('Unsaved details','Discard unsaved job details?',parent=self.root):return False
        return True
    def run(self,fn):
        try:return fn()
        except (core.TrackerError,OSError) as error:
            messagebox.showerror('Could not complete action',str(error) if isinstance(error,core.TrackerError) else 'Filesystem operation failed; partial new output may remain.',parent=self.root)
    def require(self):
        if not self.store:raise core.TrackerError('Create or open a store first')
    def current(self):
        self.require()
        if not self.loaded:raise core.TrackerError('Select a saved job first')
        if self.dirty:raise core.TrackerError('Save or refresh unsaved job details before changing its quote or status')
        return self.loaded
    def pick_new(self,title):
        return filedialog.asksaveasfilename(title=title,defaultextension='.sqlite',filetypes=[('SQLite store','*.sqlite')],confirmoverwrite=False,parent=self.root)
    def attach(self,store):
        self.store=store;self.selected=None;self.loaded=None;self.dirty=False;self.due.set('');self.filter.set('all');self.refresh();self.fill(None)
    def create(self):
        if self.okay():
            path=self.pick_new('Create a NEW store (existing files will be refused)')
            if path:self.run(lambda:self.attach(core.Store.create(path)))
    def demo(self):
        if self.okay():
            path=self.pick_new('Create a NEW fictional demo store')
            if path:self.run(lambda:self.attach(core.create_demo(path)))
    def open(self):
        if self.okay():
            path=filedialog.askopenfilename(title='Open your local tracker store',filetypes=[('SQLite store','*.sqlite')],parent=self.root)
            if path:self.run(lambda:self.attach(core.Store(path)))
    def restore(self):
        if not self.okay():return
        folder=filedialog.askdirectory(title='Select a verified tracker backup folder',parent=self.root)
        if not folder:return
        path=self.pick_new('Restore to a NEW .sqlite file')
        if path:
            def task():
                result=core.restore_backup(folder,path)
                return ('restored',result,path)
            self.background(task)
    def refresh(self,choose=None):
        if self.dirty and not self.okay():return
        self.require();rows=self.store.list_jobs(None if self.filter.get()=='all' else self.filter.get(),self.due.get() or None)
        self.loading=True
        try:
            self.tree.delete(*self.tree.get_children())
            for row in rows:self.tree.insert('', 'end',iid=row['id'],values=tuple(row[x] for x in ('title','customer','status','follow_up','version')))
            self.location.set(str(self.store.path));self.dirty=False
            identity=choose or self.selected
            if identity and self.tree.exists(identity):self.tree.selection_set(identity);self.selected=identity;self.fill(self.store.get(identity))
            else:self.selected=None;self.fill(None)
        finally:self.loading=False
    def select(self,*_):
        if self.loading:return
        selection=self.tree.selection()
        if not selection:return
        identity=selection[0]
        if self.loaded and identity==self.loaded['id']:return
        if not self.okay():
            self.loading=True
            try:
                if self.selected and self.tree.exists(self.selected):self.tree.selection_set(self.selected)
            finally:self.loading=False
            return
        self.run(lambda:self.load(identity))
    def load(self,identity):self.selected=identity;self.fill(self.store.get(identity))
    def fill(self,job):
        previous=self.loading;self.loading=True;self.loaded=job
        try:
            for key,var in self.values.items():var.set(job[key] if job else '')
            self.notes.delete('1.0','end');self.notes.insert('1.0',job['notes'] if job else '');self.notes.edit_modified(False)
            self.reference.set('');self.appointment.set('');self.amount.set('0.00');self.currency.set('USD')
            for widget in (self.scope,self.exclusions):widget.delete('1.0','end')
            lines=['Select a saved job to see its revision and activity history.']
            if job:
                lines=[f"{job['id']} | {job['status']} | version {job['version']}",f"Created {job['created_utc']} | Updated {job['updated_utc']}",'']
                for quote in job['quotes']:
                    lines.extend([f"Revision {quote['revision']}: {quote['amount']} {quote['currency']}",quote['scope'],'Exclusions: '+quote['exclusions']])
                    if quote['decision']:lines.append('Recorded '+quote['decision']['decision']+': '+quote['decision']['reference'])
                    lines.append('')
                lines.append('Activity (metadata; not a tamper-proof audit log):')
                lines.extend(f"{e['recorded_utc']} {e['action']} {e['detail_json']}" for e in job['events'])
            self.history.configure(state='normal');self.history.delete('1.0','end');self.history.insert('1.0','\n'.join(lines));self.history.configure(state='disabled')
            self.dirty=False
        finally:self.loading=previous
    def new(self):
        if self.okay():
            def action():self.require();self.selected=None;self.tree.selection_remove(*self.tree.selection());self.fill(None);self.book.select(0);self.notice.set('Enter the new job details, then Save job details.')
            self.run(action)
    def save(self):
        def action():
            self.require();raw={key:var.get() for key,var in self.values.items()};raw['notes']=self.notes.get('1.0','end-1c')
            job=self.store.edit_job(self.loaded['id'],raw,self.loaded['version']) if self.loaded else self.store.new_job(raw)
            self.dirty=False;self.refresh(job['id']);self.notice.set('Job details saved.')
        self.run(action)
    def quote(self):
        def action():
            job=self.current();raw={'amount':self.amount.get(),'currency':self.currency.get(),'scope':self.scope.get('1.0','end-1c'),'exclusions':self.exclusions.get('1.0','end-1c')}
            updated=self.store.add_quote(job['id'],raw,job['version']);self.refresh(updated['id']);self.notice.set('New revision saved; record a decision for this revision before scheduling.')
        self.run(action)
    def decision(self,state):
        def action():
            job=self.current();updated=self.store.decide(job['id'],state,self.reference.get(),job['version']);self.refresh(updated['id']);self.notice.set('Operator-supplied decision recorded for the current revision.')
        self.run(action)
    def status(self):
        def action():
            job=self.current();updated=self.store.set_status(job['id'],self.state.get(),job['version'],self.appointment.get());self.refresh(updated['id']);self.notice.set('Status recorded.')
        self.run(action)
    def output(self,kind):
        def action():
            self.require()
            if not self.okay():return
            parent=filedialog.askdirectory(title='Select a parent for a NEW '+kind+' folder',parent=self.root)
            if not parent:return
            # A unique name prevents an overwrite prompt from concealing existing output.
            target=Path(parent)/(kind+'-'+core.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+core.uuid.uuid4().hex[:6])
            store=self.store
            self.background(lambda:('done',store.backup(target,self.cancel) if kind=='backup' else core.export_report(store,target,self.cancel),str(target)))
        self.run(action)
    def backup(self):self.output('backup')
    def export(self):self.output('report')
    def background(self,fn):
        if self.worker and self.worker.is_alive():raise core.TrackerError('A background task is already running')
        self.cancel.clear();self.notice.set('Working on new output; you may cancel. Existing files are never replaced.')
        def work():
            try:self.messages.put(('ok',fn()))
            except (core.TrackerError,OSError) as error:self.messages.put(('error',str(error) if isinstance(error,core.TrackerError) else 'Filesystem operation failed; partial new output may remain.'))
            except Exception:self.messages.put(('error','Unexpected background failure; partial new output may remain.'))
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
    def poll(self):
        if self.closed:return
        if self.poll_id:self.root.after_cancel(self.poll_id);self.poll_id=None
        try:
            while True:
                kind,value=self.messages.get_nowait()
                if kind=='error':self.notice.set(value)
                else:
                    action,result,path=value
                    if action=='restored':self.run(lambda:self.attach(core.Store(path)))
                    self.notice.set('Verified '+('recovery' if action=='restored' else 'new output')+': '+path)
        except queue.Empty:pass
        self.poll_id=self.root.after(80,self.poll)
    def close(self):
        if self.worker and self.worker.is_alive():
            self.cancel.set();self.notice.set('Cancelling; wait for the operation to finish, then close again.');return
        if not self.okay():return
        self.closed=True
        if self.poll_id:self.root.after_cancel(self.poll_id);self.poll_id=None
        self.root.destroy()


def main(path=None):
    try:root=tk.Tk()
    except tk.TclError:raise core.TrackerError('Tk desktop display unavailable; use the CLI or install your OS Tk package') from None
    try:
        app=App(root,core.Store(path) if path else None)
        root.mainloop()
    finally:
        # Tk variables must be finalized on this thread, including after a worker ran.
        if 'app' in locals():del app
        import gc
        gc.collect()

if __name__=='__main__':main()
