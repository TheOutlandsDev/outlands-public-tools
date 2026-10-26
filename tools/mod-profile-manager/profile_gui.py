"""Explicit optional Tk interface for managed profile workspaces. Original MIT."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
import re


def fixed_error(error):
    value=str(error)
    return value if re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}',value) else 'OPERATION_FAILED'


def readable_result(result):
    """Human-facing summary; raw schema data requires an explicit UI choice."""
    lines=['Status: '+str(result.get('status','UNKNOWN')).replace('_',' ').title()]
    labels=[('action','Action'),('profile','Profile'),('active_before','Previously active'),
            ('active_profile','Active profile'),('outcome','Outcome'),('files','Files'),('bytes','Bytes')]
    for key,label in labels:
        if key in result:
            value=result[key]
            if value is None:value='none'
            if key in ('action','outcome'):value=str(value).replace('_',' ')
            lines.append(label+': '+str(value))
    if 'allowed' in result:lines.append('Preview allowed: '+('yes' if result['allowed'] is True else 'no'))
    if 'pending' in result:
        lines.append('Pending operation: '+('yes — review recovery before other changes' if result['pending'] else 'none'))
    profiles=result.get('profiles')
    if isinstance(profiles,list):
        lines.append('\nImported profiles: '+str(len(profiles)))
        for item in profiles:
            if isinstance(item,dict):lines.append('  '+str(item.get('id','unknown'))+' — '+str(item.get('files','?'))+' files, '+str(item.get('bytes','?'))+' bytes')
    issues=result.get('issues')
    if isinstance(issues,list) and issues:
        lines.append('\nReview items:')
        for item in issues:
            code=item.get('code','review required') if isinstance(item,dict) else str(item)
            message=('A preparation folder was retained before an operation started. It counts toward the history limit; other verified changes can continue.'
                if code=='RETAINED_PREPARATION' else str(code).replace('_',' ').capitalize())
            lines.append('  '+message)
    history=result.get('history')
    if isinstance(history,list):
        lines.append('\nRecorded operations: '+str(len(history)))
        for item in history[-10:]:
            if isinstance(item,dict):
                if item.get('action')=='preparation':lines.append('  Preparation retained before an operation started; no active change.')
                else:lines.append('  '+str(item.get('action','operation')).replace('_',' ')+' / '+str(item.get('profile') or 'none')+' / '+str(item.get('outcome') or item.get('phase') or 'pending').replace('_',' '))
        if len(history)>10:lines.append('  Showing ten records. Structured details contains the complete bounded history; records are not chronological.')
    if 'code' in result:lines.append(str(result['code']).replace('_',' ').capitalize())
    lines.append('\nChanges affect this managed workspace. Read the guide for scope and recovery limits.')
    return '\n'.join(lines)


class Controller:
    """UI-independent actions; the engine always revalidates actual files."""
    def __init__(self,api,view):self.api=api;self.view=view

    def perform(self,call):
        try:return call()
        except Exception as error:
            self.view.show_error(fixed_error(error));return None

    def refresh(self):
        def action():
            result=self.api.status(self.view.get_workspace())
            self.view.show_state(result);return result
        return self.perform(action)

    def preview(self,action='activate'):
        def inspect():
            result=self.api.plan(self.view.get_workspace(),action,
                self.view.get_profile() if action=='activate' else None)
            self.view.show_result(result);return result
        return self.perform(inspect)

    def changed(self,result):
        self.view.show_result(result);self.refresh();return result

    def initialize(self):
        def action():
            workspace=self.view.get_workspace()
            if not self.view.confirm('Create managed workspace',
                'Create a new manager-owned workspace at:\n'+workspace+
                '\n\nThe destination must be new. Its active folder and retained copies stay inside this workspace.'):
                return None
            return self.changed(self.api.initialize(workspace))
        return self.perform(action)

    def import_profile(self):
        def action():
            workspace=self.view.get_workspace();profile=self.view.get_profile();source=self.view.get_source()
            if not self.view.confirm('Copy profile into workspace',
                'Import profile '+profile+' from:\n'+source+'\n\nInto workspace:\n'+workspace+
                '\n\nThis copies supported regular-file bytes and verifies them. The selected source stays unchanged.'):
                return None
            return self.changed(self.api.import_profile(workspace,profile,source))
        return self.perform(action)

    def activate(self):return self.switch('activate')
    def deactivate(self):return self.switch('deactivate')

    def switch(self,action):
        def change():
            workspace=self.view.get_workspace();profile=self.view.get_profile() if action=='activate' else None
            inspected=self.api.plan(workspace,action,profile)
            self.view.show_result(inspected)
            if inspected.get('allowed') is not True:
                self.view.show_error('PLAN_NOT_ALLOWED');return None
            description=('Activate profile '+profile+'. A complete verified copy becomes the managed active folder.'
                         if action=='activate' else 'Deactivate the managed active folder and retain its verified tree.')
            if not self.view.confirm('Confirm '+action,
                description+'\n\nManaged workspace:\n'+workspace+
                '\n\nPrevious active data is retained. The engine rechecks state after this preview.'):
                return None
            result=self.api.activate(workspace,profile) if action=='activate' else self.api.deactivate(workspace)
            return self.changed(result)
        return self.perform(change)

    def recover(self):
        def action():
            workspace=self.view.get_workspace();current=self.api.status(workspace)
            self.view.show_state(current)
            if not current.get('pending'):
                self.view.show_result({'status':'OK','code':'NO_PENDING_OPERATION'});return current
            if not self.view.confirm('Recover pending operation',
                'Inspect and recover the pending operation in:\n'+workspace+
                '\n\nVerified work may resume. An incomplete stage may be retained with an aborted outcome. Unknown or changed data is held.'):
                return None
            return self.changed(self.api.recover(workspace))
        return self.perform(action)


class Desktop:
    """Small explicit workspace UI; no filesystem work occurs in construction."""
    def __init__(self,root,api,workspace=None):
        import tkinter as tk
        from tkinter import ttk
        self.tk=tk;self.root=root;self.workspace=tk.StringVar(value=str(workspace or ''))
        self.source=tk.StringVar();self.profile=tk.StringVar();self.summary=tk.StringVar(value='Choose a workspace, then refresh or initialize a new one.')
        self.active_path=tk.StringVar(value='Managed active folder: choose a workspace')
        self.structured=tk.BooleanVar(value=False);self.latest_result={}
        self.controller=Controller(api,self)
        root.title('OUTLANDS Mod Profile Activation Manager')
        root.geometry('1040x760');root.minsize(780,560)
        root.columnconfigure(0,weight=1);root.rowconfigure(0,weight=1)
        frame=ttk.Frame(root,padding=14);frame.grid(row=0,column=0,sticky='nsew')
        frame.columnconfigure(1,weight=1);frame.rowconfigure(8,weight=1)
        ttk.Label(frame,text='Managed Mod Profiles',font=('TkDefaultFont',16,'bold')).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,5))
        ttk.Label(frame,text='Explicit local copies, verified activation and retained history. Public examples are fictional.').grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,12))
        ttk.Label(frame,text='Workspace').grid(row=2,column=0,sticky='w')
        self.workspace_entry=ttk.Entry(frame,textvariable=self.workspace);self.workspace_entry.grid(row=2,column=1,sticky='ew',padx=8)
        ttk.Button(frame,text='Browse…',command=self.choose_workspace).grid(row=2,column=2,padx=4)
        self.init_button=ttk.Button(frame,text='Initialize new',command=self.controller.initialize);self.init_button.grid(row=2,column=3,padx=4)
        workspace_info=ttk.Frame(frame);workspace_info.grid(row=3,column=0,columnspan=4,sticky='ew',pady=(5,12));workspace_info.columnconfigure(0,weight=1)
        self.workspace_hint=ttk.Label(workspace_info,text='Browse selects an existing workspace. To initialize, type a new folder path under an existing parent.',wraplength=960)
        self.workspace_hint.grid(row=0,column=0,sticky='w')
        ttk.Label(workspace_info,textvariable=self.active_path).grid(row=1,column=0,sticky='w',pady=(5,0))
        ttk.Label(frame,text='Source folder').grid(row=4,column=0,sticky='w')
        ttk.Entry(frame,textvariable=self.source).grid(row=4,column=1,sticky='ew',padx=8)
        ttk.Button(frame,text='Browse…',command=self.choose_source).grid(row=4,column=2,padx=4)
        ttk.Label(frame,text='Profile ID').grid(row=5,column=0,sticky='w',pady=8)
        ttk.Entry(frame,textvariable=self.profile).grid(row=5,column=1,sticky='ew',padx=8)
        self.import_button=ttk.Button(frame,text='Import copy',command=self.controller.import_profile);self.import_button.grid(row=5,column=2,columnspan=2,padx=4,sticky='ew')
        ttk.Label(frame,text='IDs: lowercase letter, then lowercase letters, digits or hyphens; at most 40 characters.').grid(row=6,column=0,columnspan=4,sticky='w')
        ttk.Label(frame,textvariable=self.summary,wraplength=960).grid(row=7,column=0,columnspan=4,sticky='w',pady=10)
        area=ttk.Panedwindow(frame,orient='horizontal');area.grid(row=8,column=0,columnspan=4,sticky='nsew')
        left=ttk.Frame(area);right=ttk.Frame(area);area.add(left,weight=1);area.add(right,weight=3)
        left.columnconfigure(0,weight=1);left.rowconfigure(1,weight=1)
        ttk.Label(left,text='Imported profiles').grid(row=0,column=0,sticky='w')
        self.profiles=tk.Listbox(left,exportselection=False,height=12);self.profiles.grid(row=1,column=0,sticky='nsew',pady=6)
        self.profiles.bind('<<ListboxSelect>>',self.selected_profile)
        right.columnconfigure(0,weight=1);right.rowconfigure(1,weight=1)
        self.details_toggle=ttk.Checkbutton(right,text='Show structured details',variable=self.structured,command=self.render_result)
        self.details_toggle.grid(row=0,column=0,sticky='w',padx=(10,0))
        self.details=tk.Text(right,wrap='word',height=14,state='disabled');self.details.grid(row=1,column=0,sticky='nsew',padx=(10,0),pady=6)
        bar=ttk.Frame(frame);bar.grid(row=9,column=0,columnspan=4,sticky='ew',pady=10)
        self.refresh_button=ttk.Button(bar,text='Refresh status',command=self.controller.refresh);self.refresh_button.pack(side='left',padx=3)
        self.preview_button=ttk.Button(bar,text='Preview activation',command=self.controller.preview);self.preview_button.pack(side='left',padx=3)
        self.activate_button=ttk.Button(bar,text='Activate…',command=self.controller.activate);self.activate_button.pack(side='left',padx=3)
        self.deactivate_button=ttk.Button(bar,text='Deactivate…',command=self.controller.deactivate);self.deactivate_button.pack(side='left',padx=3)
        self.recover_button=ttk.Button(bar,text='Recover pending…',command=self.controller.recover);self.recover_button.pack(side='left',padx=3)
        ttk.Label(frame,text='Activation affects this workspace’s active folder. Game-specific integration is a separate manual decision.\nClose programs using managed files before changes. Verification may temporarily occupy this window.',wraplength=960).grid(row=10,column=0,columnspan=4,sticky='w')
        self.workspace.trace_add('write',lambda *_:self.update_active_path());self.update_active_path()

    def update_active_path(self):
        value=self.workspace.get()
        self.active_path.set('Managed active folder: '+str(Path(value)/'active') if value else 'Managed active folder: choose a workspace')

    def get_workspace(self):return self.workspace.get()
    def get_source(self):return self.source.get()
    def get_profile(self):return self.profile.get()

    def choose_workspace(self):
        from tkinter import filedialog
        value=filedialog.askdirectory(parent=self.root,title='Choose an existing workspace; type a new path to initialize',mustexist=True)
        if value:self.workspace.set(value)

    def choose_source(self):
        from tkinter import filedialog
        value=filedialog.askdirectory(parent=self.root,title='Select a profile source to copy',mustexist=True)
        if value:self.source.set(value)

    def selected_profile(self,_event=None):
        selected=self.profiles.curselection()
        if selected:self.profile.set(self.profiles.get(selected[0]))

    def confirm(self,title,message):
        from tkinter import messagebox
        return bool(messagebox.askyesno(title,message,parent=self.root,default='no'))

    def show_error(self,code):
        from tkinter import messagebox
        self.summary.set('Review required: '+code)
        messagebox.showerror('Profile operation stopped',code+'\nThe operation stopped. Review the guide and current workspace state before another change.',parent=self.root)

    def show_state(self,result):
        selected=self.profile.get();self.profiles.delete(0,'end')
        for item in result.get('profiles',[]):self.profiles.insert('end',item['id'])
        for index,item in enumerate(self.profiles.get(0,'end')):
            if item==selected:self.profiles.selection_set(index)
        active=result.get('active_profile');pending=result.get('pending')
        self.summary.set('Status: '+result.get('status','UNKNOWN')+' | Active: '+str(active or 'none')+' | Pending: '+str(pending or 'none'))
        self.show_result(result)

    def show_result(self,result):
        self.latest_result=result;self.render_result()

    def render_result(self):
        result=self.latest_result
        text=json.dumps(result,indent=2,ensure_ascii=True,allow_nan=False) if self.structured.get() else readable_result(result)
        self.details.configure(state='normal');self.details.delete('1.0','end')
        self.details.insert('1.0',text);self.details.configure(state='disabled')


def main(workspace=None):
    root=None
    try:
        import tkinter as tk
        root=tk.Tk();api=importlib.import_module('profile_engine');view=Desktop(root,api,workspace)
        if workspace:view.controller.refresh()
        root.mainloop();return 0
    except (ImportError,RuntimeError,OSError) as error:
        print(json.dumps({'status':'INCOMPLETE','error':'GUI_UNAVAILABLE'},sort_keys=True));return 2
    except Exception as error:
        print(json.dumps({'status':'INCOMPLETE','error':'GUI_UNAVAILABLE'},sort_keys=True));return 2
    finally:
        if root is not None:
            try:root.destroy()
            except Exception:pass


if __name__=='__main__':raise SystemExit(main())
