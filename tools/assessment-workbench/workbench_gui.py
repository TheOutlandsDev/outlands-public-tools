"""Guided Tk drafts; all persistent I/O belongs to the workbench core."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import workbench_core as core

COLLECTIONS = {
    "submission": "submissions",
    "finding": "findings",
    "retest": "retests",
}
FIELDS = {
    "submission": ("id", "series_id", "revision"),
    "finding": ("id", "submission_id", "state", "selected_retest_id"),
    "retest": ("id", "finding_id", "submission_id", "outcome"),
}
STATES = ("open", "retest_pending", "closure_claimed")
OUTCOMES = ("not_run", "still_present", "not_observed", "inconclusive")
NONE = "(none)"


class WorkbenchApp:
    """One local editor with explicit draft commits and guarded core operations."""

    def __init__(self, root):
        self.root = root
        self.store_path = None
        self.revision = 0
        self.draft = core.empty_records()
        self.saved_records = copy.deepcopy(self.draft)
        self.dirty = False
        self.form_dirty = set()
        self.forms = {}
        self.form_widgets = {}
        self.tables = {}
        self.buttons = {}
        self.selected_ids = {kind: None for kind in COLLECTIONS}
        self._loading_forms = False
        self._rendering = False
        self._last_status = "EMPTY_WORKSPACE"
        self.closed = False
        self.status_var = tk.StringVar(root)
        self.location_var = tk.StringVar(root, value="No private store selected.")
        root.title("OUTLANDS | Offline Assessment Workbench")
        root.geometry("1140x830")
        root.minsize(940, 710)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.report_callback_exception = self._callback_error
        self._build()
        self._render_tables()
        self.validate_draft()

    def _build(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Offline Assessment Workbench",
            font=("TkDefaultFont", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text="Private declarations only. Outcomes, authorization and isolation remain unverified.",
            wraplength=1070,
        ).pack(anchor="w", pady=(4, 10))
        bar = ttk.Frame(outer)
        bar.pack(fill="x")
        for title, action in (
            ("Create store", self.create_store),
            ("Open store", self.open_store),
            ("Fictional demo", self.create_demo),
            ("Import to NEW store", self.import_records),
            ("Export saved JSON", self.export_saved),
            ("Clone saved store", self.clone_saved),
        ):
            ttk.Button(bar, text=title, command=action).pack(side="left", padx=(0, 5))
        ttk.Label(outer, textvariable=self.location_var, wraplength=1070).pack(
            anchor="w", pady=(8, 3)
        )
        ttk.Label(outer, textvariable=self.status_var, wraplength=1070).pack(
            anchor="w", pady=(0, 8)
        )
        book = ttk.Notebook(outer)
        book.pack(fill="both", expand=True)
        self.notebook = book
        for kind, collection in COLLECTIONS.items():
            panel = ttk.Frame(book, padding=10)
            book.add(panel, text=collection.title())
            self._build_editor(panel, kind)
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(10, 6))
        for key, title, action in (
            ("validate", "Validate draft", self.validate_draft),
            ("save", "Save draft", self.save_draft),
            ("refresh", "Refresh saved store", self.refresh),
            ("history", "Read-only history", self.show_history),
        ):
            button = ttk.Button(bar, text=title, command=action)
            button.pack(side="left", padx=(0, 6))
            self.buttons[key] = button
        ttk.Label(
            outer,
            text="Apply form changes to the draft, then Save. Removing a record retains earlier saved history.",
            wraplength=1070,
        ).pack(anchor="w", pady=(0, 5))
        self.validation_text = tk.Text(outer, height=8, wrap="word", state="disabled")
        self.validation_text.pack(fill="x")

    def _build_editor(self, parent, kind):
        fields = FIELDS[kind]
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        table = ttk.Treeview(
            table_frame, columns=fields, show="headings", selectmode="browse", height=8
        )
        for field in fields:
            table.heading(field, text=field.replace("_", " ").title())
            table.column(field, width=185, minwidth=110)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        table.bind(
            "<<TreeviewSelect>>",
            lambda _event, selected_kind=kind: self._select_event(selected_kind),
        )
        self.tables[kind] = table
        form = ttk.Frame(parent)
        form.pack(fill="x", pady=(12, 4))
        self.forms[kind] = {}
        self.form_widgets[kind] = {}
        for index, field in enumerate(fields):
            ttk.Label(form, text=field.replace("_", " ").title()).grid(
                row=index, column=0, sticky="w", padx=(0, 10), pady=3
            )
            variable = tk.StringVar(self.root)
            self.forms[kind][field] = variable
            if field in {"submission_id", "finding_id", "selected_retest_id"}:
                widget = ttk.Combobox(form, textvariable=variable, state="readonly")
            elif field in {"state", "outcome"}:
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=STATES if field == "state" else OUTCOMES,
                    state="readonly",
                )
            else:
                widget = ttk.Entry(form, textvariable=variable)
            widget.grid(row=index, column=1, sticky="ew", pady=3)
            self.form_widgets[kind][field] = widget
            variable.trace_add(
                "write",
                lambda *_args, selected_kind=kind: self._form_changed(selected_kind),
            )
        form.columnconfigure(1, weight=1)
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(5, 0))
        for key, title, action in (
            ("clear", "New / clear form", lambda: self.clear_form(kind)),
            ("apply", "Apply form to draft", lambda: self.on_apply_form(kind)),
            (
                "remove",
                "Remove selected from draft",
                lambda: self.on_remove_selected(kind),
            ),
        ):
            button = ttk.Button(bar, text=title, command=action)
            button.pack(side="left", padx=(0, 6))
            self.buttons[f"{kind}_{key}"] = button
        self._load_form(kind, None)

    def _callback_error(self, _exception, _value, _traceback):
        self._show_error("GUI_OPERATION_FAILED")

    def _show_error(self, code):
        self._last_status = code
        self._render_status()
        detail = code
        if "CONFLICT" in code or "STALE" in code:
            detail += "\nDraft retained. Refresh discards it and loads saved records; no merge is automatic."
        messagebox.showerror("Workbench operation", detail, parent=self.root)

    def _call(self, operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except core.WorkbenchError as error:
            self._show_error(str(error))
        except Exception:
            self._show_error("WORKBENCH_OPERATION_FAILED")
        return None

    def _render_status(self):
        location = (
            "No store" if self.store_path is None else f"Saved revision {self.revision}"
        )
        changes = []
        if self.dirty:
            changes.append("UNSAVED DRAFT")
        if self.form_dirty:
            changes.append("UNAPPLIED FORM CHANGES")
        self.status_var.set(" | ".join([location, *changes, self._last_status]))

    def _form_changed(self, kind):
        if not self._loading_forms:
            self.form_dirty.add(kind)
            self._render_status()

    def _has_unsaved(self):
        return self.dirty or bool(self.form_dirty)

    def _confirm_discard(self):
        return not self._has_unsaved() or messagebox.askyesno(
            "Unsaved changes",
            "Discard unsaved draft and unapplied form changes? Saved history is retained.",
            parent=self.root,
        )

    def _confirm_form_discard(self, kind):
        return kind not in self.form_dirty or messagebox.askyesno(
            "Unapplied form changes",
            "Discard unapplied changes in this form? The draft is unchanged.",
            parent=self.root,
        )

    def _load_form(self, kind, record):
        defaults = {"revision": "1", "state": "open", "outcome": "not_run"}
        self._loading_forms = True
        try:
            for field, variable in self.forms[kind].items():
                value = (
                    record.get(field) if record is not None else defaults.get(field, "")
                )
                if field == "selected_retest_id":
                    value = NONE if value is None or record is None else value
                variable.set(str(value))
            self.form_widgets[kind]["id"].configure(
                state="readonly" if record is not None else "normal"
            )
        finally:
            self._loading_forms = False
        self.form_dirty.discard(kind)
        self._sync_ref_choices()
        self._render_status()

    def _sync_ref_choices(self):
        sources = {
            "submission_id": [row["id"] for row in self.draft["submissions"]],
            "finding_id": [row["id"] for row in self.draft["findings"]],
            "selected_retest_id": [NONE, *[row["id"] for row in self.draft["retests"]]],
        }
        for kind, widgets in self.form_widgets.items():
            for field, widget in widgets.items():
                if field not in sources:
                    continue
                choices = list(sources[field])
                current = self.forms[kind][field].get()
                if current and current not in choices:
                    choices.append(current)
                widget.configure(values=choices)

    def _render_tables(self):
        self._rendering = True
        try:
            for kind, collection in COLLECTIONS.items():
                table = self.tables[kind]
                table.delete(*table.get_children())
                for record in self.draft[collection]:
                    table.insert(
                        "",
                        "end",
                        iid=record["id"],
                        values=[
                            NONE if record[field] is None else record[field]
                            for field in FIELDS[kind]
                        ],
                    )
                selected = self.selected_ids[kind]
                if selected is not None and table.exists(selected):
                    table.selection_set(selected)
                elif selected is not None:
                    self.selected_ids[kind] = None
                    self._load_form(kind, None)
        finally:
            self._rendering = False
        self._sync_ref_choices()

    def _select_event(self, kind):
        if self._rendering:
            return
        selected = self.tables[kind].selection()
        if selected and selected[0] != self.selected_ids[kind]:
            if not self.select_record(kind, selected[0]):
                previous = self.selected_ids[kind]
                if previous is not None and self.tables[kind].exists(previous):
                    self.tables[kind].selection_set(previous)
                else:
                    self.tables[kind].selection_remove(*selected)

    def set_snapshot(self, path, snapshot):
        self.store_path = Path(path)
        self.revision = snapshot["revision"]
        self.draft = copy.deepcopy(snapshot["records"])
        self.saved_records = copy.deepcopy(self.draft)
        self.dirty = False
        self.form_dirty.clear()
        self.location_var.set(f"Private store: {self.store_path}")
        self.selected_ids = {kind: None for kind in COLLECTIONS}
        for kind in COLLECTIONS:
            self._load_form(kind, None)
        self._render_tables()
        self._display_validation(snapshot["validation"])
        return snapshot

    def select_record(self, kind, identifier):
        if kind not in COLLECTIONS:
            self._show_error("RECORD_KIND_INVALID")
            return False
        record = next(
            (row for row in self.draft[COLLECTIONS[kind]] if row["id"] == identifier),
            None,
        )
        if record is None:
            self._show_error("RECORD_NOT_SELECTED")
            return False
        if not self._confirm_form_discard(kind):
            return False
        self.selected_ids[kind] = identifier
        self._load_form(kind, record)
        self.tables[kind].selection_set(identifier)
        self.tables[kind].see(identifier)
        return True

    def clear_form(self, kind):
        if not self._confirm_form_discard(kind):
            return False
        self.selected_ids[kind] = None
        self.tables[kind].selection_remove(*self.tables[kind].selection())
        self._load_form(kind, None)
        return True

    def apply_record(self, kind, record, old_id=None):
        if kind not in COLLECTIONS or not isinstance(record, dict):
            self._show_error("RECORD_FORM_INVALID")
            return False
        if old_id is not None and record.get("id") != old_id:
            self._show_error("RECORD_ID_IMMUTABLE")
            return False
        candidate = copy.deepcopy(self.draft)
        rows = candidate[COLLECTIONS[kind]]
        if old_id is None:
            rows.append(copy.deepcopy(record))
        else:
            indexes = [index for index, row in enumerate(rows) if row["id"] == old_id]
            if not indexes:
                self._show_error("RECORD_NOT_SELECTED")
                return False
            rows[indexes[0]] = copy.deepcopy(record)
        validation = self._call(core.validate_records, candidate)
        if validation is None:
            return False
        self.draft = candidate
        self.dirty = self.draft != self.saved_records
        self.selected_ids[kind] = record["id"]
        self._load_form(kind, record)
        self._render_tables()
        self._display_validation(validation)
        return True

    def remove_record(self, kind, identifier):
        if kind not in COLLECTIONS:
            self._show_error("RECORD_KIND_INVALID")
            return False
        candidate = copy.deepcopy(self.draft)
        rows = candidate[COLLECTIONS[kind]]
        remaining = [row for row in rows if row["id"] != identifier]
        if len(remaining) == len(rows):
            self._show_error("RECORD_NOT_SELECTED")
            return False
        candidate[COLLECTIONS[kind]] = remaining
        validation = self._call(core.validate_records, candidate)
        if validation is None:
            return False
        self.draft = candidate
        self.dirty = self.draft != self.saved_records
        if self.selected_ids[kind] == identifier:
            self.selected_ids[kind] = None
            self._load_form(kind, None)
        self._render_tables()
        self._display_validation(validation)
        return True

    def on_apply_form(self, kind):
        record = {field: variable.get() for field, variable in self.forms[kind].items()}
        if kind == "submission":
            raw = record["revision"]
            if not re.fullmatch(r"[1-9][0-9]{0,9}", raw) or int(raw) > 1000000000:
                self._show_error("REVISION_FORM_INVALID")
                return False
            record["revision"] = int(raw)
        if kind == "finding" and record["selected_retest_id"] == NONE:
            record["selected_retest_id"] = None
        return self.apply_record(kind, record, old_id=self.selected_ids[kind])

    def on_remove_selected(self, kind):
        identifier = self.selected_ids[kind]
        if identifier is None:
            self._show_error("RECORD_NOT_SELECTED")
            return False
        return self.remove_record(kind, identifier)

    def _display_validation(self, validation):
        self._last_status = validation["status"]
        lines = [validation["status"], *validation["issues"]]
        report = validation["report"]
        if report is not None:
            lines.extend(
                f"{row['id']} | {row['kind']} | {row['status']} | {row['evidence']}"
                for row in report["checks"]
            )
        self.validation_text.configure(state="normal")
        self.validation_text.delete("1.0", "end")
        self.validation_text.insert("1.0", "\n".join(lines))
        self.validation_text.configure(state="disabled")
        self._render_status()

    def validate_draft(self):
        validation = self._call(core.validate_records, self.draft)
        if validation is not None:
            self._display_validation(validation)
        return validation

    def save_draft(self):
        if self.store_path is None:
            self._show_error("STORE_NOT_SELECTED")
            return None
        if self.form_dirty:
            self._show_error("UNAPPLIED_FORM_CHANGES")
            return None
        if not self.dirty:
            self.validate_draft()
            return None
        snapshot = self._call(
            core.save_records,
            self.store_path,
            self.draft,
            expected_revision=self.revision,
        )
        if snapshot is not None:
            self.set_snapshot(self.store_path, snapshot)
        return snapshot

    def refresh(self):
        if self.store_path is None:
            self._show_error("STORE_NOT_SELECTED")
            return None
        if not self._confirm_discard():
            return None
        snapshot = self._call(core.load_store, self.store_path)
        if snapshot is not None:
            self.set_snapshot(self.store_path, snapshot)
        return snapshot

    def _new_store_filename(self, title):
        return filedialog.asksaveasfilename(
            parent=self.root,
            title=title + " (NEW private file outside checkout)",
            defaultextension=".sqlite",
            filetypes=[("SQLite store", "*.sqlite"), ("All files", "*")],
            confirmoverwrite=False,
        )

    def create_store(self):
        return self._create(core.create_store, "Create empty store")

    def create_demo(self):
        return self._create(core.create_demo, "Create fictional demo")

    def _create(self, operation, title):
        if not self._confirm_discard():
            return None
        path = self._new_store_filename(title)
        if not path:
            return None
        snapshot = self._call(operation, path)
        if snapshot is not None:
            self.set_snapshot(path, snapshot)
        return snapshot

    def open_store(self):
        if not self._confirm_discard():
            return None
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open private store",
            filetypes=[("SQLite store", "*.sqlite"), ("All files", "*")],
        )
        if not path:
            return None
        snapshot = self._call(core.load_store, path)
        if snapshot is not None:
            self.set_snapshot(path, snapshot)
        return snapshot

    def import_records(self):
        if not self._confirm_discard():
            return None
        input_json = filedialog.askopenfilename(
            parent=self.root,
            title="Select private neutral ledger JSON",
            filetypes=[("JSON ledger", "*.json"), ("All files", "*")],
        )
        if not input_json:
            return None
        path = self._new_store_filename("Import into NEW store")
        if not path:
            return None
        snapshot = self._call(core.import_to_new_store, input_json, path)
        if snapshot is not None:
            self.set_snapshot(path, snapshot)
        return snapshot

    def export_saved(self):
        if self.store_path is None:
            self._show_error("STORE_NOT_SELECTED")
            return None
        if self._has_unsaved():
            self._show_error("SAVE_OR_REFRESH_BEFORE_EXPORT")
            return None
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export NEW private ledger JSON",
            defaultextension=".json",
            filetypes=[("JSON ledger", "*.json"), ("All files", "*")],
            confirmoverwrite=False,
        )
        if not path:
            return None
        result = self._call(core.export_records, self.store_path, path)
        if result is not None:
            messagebox.showinfo(
                "Private export",
                f"Saved revision {result['revision']} exported. Real ledger exports remain private.",
                parent=self.root,
            )
        return result

    def clone_saved(self, revision=None, source_path=None):
        if self.store_path is None:
            self._show_error("STORE_NOT_SELECTED")
            return None
        if self._has_unsaved():
            self._show_error("SAVE_OR_REFRESH_BEFORE_CLONE")
            return None
        path = self._new_store_filename("Clone validated saved history")
        if not path:
            return None
        source = self.store_path if source_path is None else source_path
        result = self._call(core.clone_store, source, path, revision=revision)
        if result is not None:
            messagebox.showinfo(
                "Private recovery clone",
                f"New store created through saved revision {result['revision']}. Current editor is unchanged.",
                parent=self.root,
            )
        return result

    def show_history(self):
        if self.store_path is None:
            self._show_error("STORE_NOT_SELECTED")
            return None
        source_path = self.store_path
        history = self._call(core.list_history, source_path)
        if history is None:
            return None
        window = tk.Toplevel(self.root)
        window.title("Read-only saved history")
        window.geometry("880x590")
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Saved declarations only. History retains removed records and is not signed or tamper-proof.",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 8))
        columns = ("revision", "operation", "status", "empty")
        table = ttk.Treeview(frame, columns=columns, show="headings", height=7)
        for field in columns:
            table.heading(field, text=field.title())
            table.column(field, width=170)
        for entry in history:
            table.insert(
                "",
                "end",
                iid=str(entry["revision"]),
                values=[entry[field] for field in columns],
            )
        table.pack(fill="x")
        preview = tk.Text(frame, state="disabled", wrap="word", height=15)
        preview.pack(fill="both", expand=True, pady=8)

        def selected_revision():
            selected = table.selection()
            return int(selected[0]) if selected else None

        def display(_event=None):
            revision = selected_revision()
            if revision is None:
                return
            snapshot = self._call(core.load_revision, source_path, revision)
            if snapshot is not None:
                text = json.dumps(snapshot["records"], indent=2, ensure_ascii=True)
                preview.configure(state="normal")
                preview.delete("1.0", "end")
                preview.insert("1.0", text)
                preview.configure(state="disabled")

        def clone_selected():
            revision = selected_revision()
            if revision is None:
                self._show_error("HISTORY_REVISION_NOT_SELECTED")
                return
            self.clone_saved(revision=revision, source_path=source_path)

        table.bind("<<TreeviewSelect>>", display)
        ttk.Button(
            frame, text="Clone selected history to NEW store", command=clone_selected
        ).pack(anchor="w")
        return window

    def close(self):
        if self.closed or not self._confirm_discard():
            return False
        self.closed = True
        self.root.destroy()
        return True


def main():
    try:
        root = tk.Tk()
    except tk.TclError:
        raise core.WorkbenchError("TK_UNAVAILABLE") from None
    WorkbenchApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except core.WorkbenchError as error:
        print(json.dumps({"status": "ERROR", "code": str(error)}))
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        print(json.dumps({"status": "ERROR", "code": "INTERRUPTED"}))
        raise SystemExit(130) from None
    except Exception:
        print(json.dumps({"status": "ERROR", "code": "GUI_OPERATION_FAILED"}))
        raise SystemExit(2) from None
