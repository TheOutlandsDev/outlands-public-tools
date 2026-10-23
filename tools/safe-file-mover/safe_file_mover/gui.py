"""Portable Tkinter desktop interface for :mod:`safe_file_mover`.

All potentially slow engine and journal calls run on a worker thread.  Worker
threads communicate with Tk through a queue, which is drained by ``after`` on
the UI thread; a worker never reads or updates a Tk widget directly.
"""

from __future__ import annotations

import queue
import threading
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .core import (
    ConflictPolicy,
    MoveOperation,
    MovePlan,
    Progress,
    SafeMoveEngine,
    SafeMoveError,
    is_remote_path,
)


RECOVERABLE_STATUSES = frozenset(
    {
        "planned",
        "copying",
        "verified",
        "destination_committed",
        "restoring",
        "purging",
    }
)
ABANDONABLE_STATUSES = frozenset({"planned", "copying", "verified"})

ProgressReporter = Callable[[Progress], None]
Worker = Callable[[ProgressReporter], Any]


class SafeFileMoverApp:
    """A small, responsive desktop client around :class:`SafeMoveEngine`."""

    _POLL_INTERVAL_MS = 75

    def __init__(
        self,
        root: tk.Tk,
        state_directory: Path | str | None = None,
    ) -> None:
        self.root = root
        self.engine = SafeMoveEngine(state_directory)
        self._events: queue.Queue[tuple[Any, ...]] = queue.Queue()
        self._operations: dict[str, MoveOperation] = {}
        self._busy = False
        self._closing = False
        self._refresh_after_job = False

        self.root.title("Safe File Mover")
        self.root.geometry("1100x760")
        self.root.minsize(820, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._configure_style()
        self._build_ui()
        self.root.after(self._POLL_INTERVAL_MS, self._poll_events)
        self.root.after_idle(self.refresh_operations)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        if "vista" in available:
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("TkDefaultFont", 16, "bold"))
        style.configure("Subtle.TLabel", foreground="#555555")
        style.configure("Danger.TButton", foreground="#8b0000")

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=(16, 14, 16, 10))
        shell.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)
        shell.columnconfigure(0, weight=1)

        ttk.Label(shell, text="Safe File Mover", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            shell,
            text=(
                "Copy, SHA-256 verify, commit, and retain a recovery copy without "
                "overwriting existing data."
            ),
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 12))

        self.notebook = ttk.Notebook(shell)
        self.notebook.grid(row=2, column=0, sticky="nsew")

        self.move_tab = ttk.Frame(self.notebook, padding=14)
        self.recovery_tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.move_tab, text="Move")
        self.notebook.add(self.recovery_tab, text="Recovery")

        self._build_move_tab()
        self._build_recovery_tab()

        state_text = f"Journal: {self.engine.journal.database_path}"
        self.app_status_var = tk.StringVar(value="Ready")
        footer = ttk.Frame(shell)
        footer.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.app_status_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(footer, text=state_text, style="Subtle.TLabel").grid(
            row=0, column=1, sticky="e", padx=(16, 0)
        )

    def _build_move_tab(self) -> None:
        tab = self.move_tab
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(8, weight=1)

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.new_name_var = tk.StringVar()
        self.conflict_var = tk.StringVar(value=ConflictPolicy.FAIL.value)
        self.keep_backup_var = tk.BooleanVar(value=True)

        ttk.Label(tab, text="Source file or folder").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self.source_entry = ttk.Entry(tab, textvariable=self.source_var)
        self.source_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(tab, text="Choose file…", command=self._choose_source_file).grid(
            row=0, column=2, padx=(8, 0), pady=4
        )
        ttk.Button(tab, text="Choose folder…", command=self._choose_source_folder).grid(
            row=0, column=3, padx=(6, 0), pady=4
        )

        ttk.Label(tab, text="Destination folder").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self.destination_entry = ttk.Entry(tab, textvariable=self.destination_var)
        self.destination_entry.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(tab, text="Choose folder…", command=self._choose_destination).grid(
            row=1, column=2, columnspan=2, sticky="e", padx=(8, 0), pady=4
        )

        ttk.Label(tab, text="New name (optional)").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self.new_name_entry = ttk.Entry(tab, textvariable=self.new_name_var)
        self.new_name_entry.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(
            tab,
            text="One filename only; leave blank to keep the current name.",
            style="Subtle.TLabel",
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=4)

        options = ttk.LabelFrame(tab, text="Safety options", padding=10)
        options.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(12, 8))
        options.columnconfigure(2, weight=1)
        ttk.Label(options, text="If the destination name exists:").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Radiobutton(
            options,
            text="Fail safely",
            value=ConflictPolicy.FAIL.value,
            variable=self.conflict_var,
        ).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Radiobutton(
            options,
            text="Choose a numbered name",
            value=ConflictPolicy.RENAME.value,
            variable=self.conflict_var,
        ).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(
            options,
            text="Keep the original as a recovery copy after the move (recommended)",
            variable=self.keep_backup_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(9, 0))

        action_row = ttk.Frame(tab)
        action_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(4, 10))
        action_row.columnconfigure(0, weight=1)
        self.preview_button = ttk.Button(
            action_row, text="Preview", command=self.preview_move
        )
        self.preview_button.grid(row=0, column=1, padx=(0, 8))
        self.move_button = ttk.Button(action_row, text="Move", command=self.start_move)
        self.move_button.grid(row=0, column=2)

        progress_box = ttk.Frame(tab)
        progress_box.grid(row=5, column=0, columnspan=4, sticky="ew")
        progress_box.columnconfigure(0, weight=1)
        self.move_progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_box, textvariable=self.move_progress_var).grid(
            row=0, column=0, sticky="w"
        )
        self.move_progress = ttk.Progressbar(
            progress_box, mode="determinate", maximum=100
        )
        self.move_progress.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.move_progress_path_var = tk.StringVar()
        ttk.Label(
            progress_box,
            textvariable=self.move_progress_path_var,
            style="Subtle.TLabel",
        ).grid(row=2, column=0, sticky="w")

        ttk.Separator(tab).grid(
            row=6, column=0, columnspan=4, sticky="ew", pady=(10, 8)
        )
        ttk.Label(tab, text="Activity log").grid(
            row=7, column=0, columnspan=4, sticky="w"
        )
        self.move_log = ScrolledText(
            tab,
            height=10,
            wrap="word",
            state="disabled",
            font=("TkFixedFont", 9),
        )
        self.move_log.grid(
            row=8, column=0, columnspan=4, sticky="nsew", pady=(4, 0)
        )

    def _build_recovery_tab(self) -> None:
        tab = self.recovery_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=3)
        tab.rowconfigure(7, weight=1)

        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        self.refresh_button = ttk.Button(
            toolbar, text="Refresh", command=self.refresh_operations
        )
        self.refresh_button.grid(row=0, column=0, sticky="w")
        self.show_complete_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toolbar,
            text="Show completed operations",
            variable=self.show_complete_var,
            command=self.refresh_operations,
        ).grid(row=0, column=2, sticky="e")

        ttk.Label(
            tab,
            text=(
                "Interrupted moves can be resumed. Retained recovery copies can be "
                "restored or permanently purged after verification."
            ),
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="ew", pady=(8, 6))

        tree_frame = ttk.Frame(tab)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        columns = ("operation", "status", "source", "destination", "size", "recovery")
        self.operations_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "operation": "Operation ID",
            "status": "Status",
            "source": "Source",
            "destination": "Destination",
            "size": "Data",
            "recovery": "Recovery copy",
        }
        widths = {
            "operation": 190,
            "status": 145,
            "source": 260,
            "destination": 260,
            "size": 95,
            "recovery": 260,
        }
        for column in columns:
            self.operations_tree.heading(column, text=headings[column])
            self.operations_tree.column(
                column,
                width=widths[column],
                minwidth=70,
                stretch=column in {"source", "destination", "recovery"},
            )
        vertical = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.operations_tree.yview
        )
        horizontal = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self.operations_tree.xview
        )
        self.operations_tree.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set
        )
        self.operations_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.operations_tree.bind("<<TreeviewSelect>>", self._on_operation_selected)
        self.operations_tree.tag_configure("attention", foreground="#9a5b00")
        self.operations_tree.tag_configure("retained", foreground="#0b5f9e")
        self.operations_tree.tag_configure("failed", foreground="#9b1c1c")

        self.operation_detail_var = tk.StringVar(
            value="Select an operation to see its paths and available actions."
        )
        ttk.Label(
            tab,
            textvariable=self.operation_detail_var,
            justify="left",
            wraplength=1000,
        ).grid(row=3, column=0, sticky="ew", pady=(8, 7))

        actions = ttk.Frame(tab)
        actions.grid(row=4, column=0, sticky="ew")
        self.recover_button = ttk.Button(
            actions, text="Recover", command=self.recover_selected, state="disabled"
        )
        self.restore_button = ttk.Button(
            actions, text="Restore", command=self.restore_selected, state="disabled"
        )
        self.purge_button = ttk.Button(
            actions,
            text="Purge",
            command=self.purge_selected,
            state="disabled",
            style="Danger.TButton",
        )
        self.abandon_button = ttk.Button(
            actions, text="Abandon", command=self.abandon_selected, state="disabled"
        )
        self.recover_button.grid(row=0, column=0, padx=(0, 7))
        self.restore_button.grid(row=0, column=1, padx=(0, 7))
        self.purge_button.grid(row=0, column=2, padx=(0, 7))
        self.abandon_button.grid(row=0, column=3)

        progress_box = ttk.Frame(tab)
        progress_box.grid(row=5, column=0, sticky="ew", pady=(9, 0))
        progress_box.columnconfigure(0, weight=1)
        self.recovery_progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_box, textvariable=self.recovery_progress_var).grid(
            row=0, column=0, sticky="w"
        )
        self.recovery_progress = ttk.Progressbar(
            progress_box, mode="determinate", maximum=100
        )
        self.recovery_progress.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.recovery_progress_path_var = tk.StringVar()
        ttk.Label(
            progress_box,
            textvariable=self.recovery_progress_path_var,
            style="Subtle.TLabel",
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(tab, text="Recovery log").grid(
            row=6, column=0, sticky="w", pady=(9, 0)
        )
        self.recovery_log = ScrolledText(
            tab,
            height=6,
            wrap="word",
            state="disabled",
            font=("TkFixedFont", 9),
        )
        self.recovery_log.grid(row=7, column=0, sticky="nsew", pady=(4, 0))

    def _choose_source_file(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a source file",
            initialdir=self._initial_directory(self.source_var.get()),
        )
        if selected:
            self.source_var.set(selected)

    def _choose_source_folder(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            title="Choose a source folder",
            initialdir=self._initial_directory(self.source_var.get()),
            mustexist=True,
        )
        if selected:
            self.source_var.set(selected)

    def _choose_destination(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            title="Choose a destination folder",
            initialdir=self._initial_directory(self.destination_var.get()),
            mustexist=True,
        )
        if selected:
            self.destination_var.set(selected)

    @staticmethod
    def _initial_directory(value: str) -> str | None:
        if not value.strip():
            return None
        path = Path(value).expanduser()
        if path.is_dir():
            return str(path)
        if path.parent.is_dir():
            return str(path.parent)
        return None

    def _move_arguments(self) -> tuple[str, str, str | None, str, bool] | None:
        source = self.source_var.get().strip()
        destination = self.destination_var.get().strip()
        if not source or not destination:
            messagebox.showerror(
                "Source and destination required",
                "Choose a source file or folder and a destination folder.",
                parent=self.root,
            )
            return None
        new_name_text = self.new_name_var.get().strip()
        return (
            source,
            destination,
            new_name_text or None,
            self.conflict_var.get(),
            self.keep_backup_var.get(),
        )

    def preview_move(self) -> None:
        arguments = self._move_arguments()
        if arguments is None:
            return
        source, destination, new_name, conflict, _keep_backup = arguments
        self._append_log("move", f"Previewing {source} -> {destination}")
        self._start_job(
            "preview",
            "move",
            lambda _progress: self.engine.plan(
                source,
                destination,
                new_name=new_name,
                conflict_policy=conflict,
            ),
        )

    def start_move(self) -> None:
        arguments = self._move_arguments()
        if arguments is None:
            return
        source, destination, new_name, conflict, keep_backup = arguments
        if not keep_backup and is_remote_path(destination):
            messagebox.showerror(
                "Keep a recovery copy for remote moves",
                (
                    "Automatic recovery-copy deletion is disabled when the "
                    "destination is a network share. Keep the recovery copy, validate "
                    "the moved application data, then use Purge with the separate "
                    "remote-risk confirmation."
                ),
                parent=self.root,
            )
            return
        final_name = new_name or Path(source).name
        recovery_text = (
            "The original will be retained as a recovery copy."
            if keep_backup
            else (
                "The recovery copy will be permanently removed after primary-content "
                "verification. Close every program using these paths first; filesystem "
                "ACL/ownership details are not part of that verification."
            )
        )
        confirmed = messagebox.askyesno(
            "Start verified move?",
            (
                f"Source:\n{source}\n\nDestination:\n{Path(destination) / final_name}\n\n"
                f"{recovery_text}\n\nContinue?"
            ),
            parent=self.root,
            icon="question",
            default="no",
        )
        if not confirmed:
            return
        self._append_log("move", f"Starting verified move: {source} -> {destination}")
        self._start_job(
            "move",
            "move",
            lambda progress: self.engine.move(
                source,
                destination,
                new_name=new_name,
                conflict_policy=conflict,
                keep_backup=keep_backup,
                progress=progress,
            ),
        )

    def refresh_operations(self) -> None:
        if self._busy:
            self._refresh_after_job = True
            return
        include_complete = self.show_complete_var.get()
        self._start_job(
            "refresh",
            "recovery",
            lambda _progress: self.engine.list_operations(
                include_complete=include_complete
            ),
            quiet=True,
        )

    def recover_selected(self) -> None:
        operation = self._selected_operation()
        if operation is None:
            return
        self._append_log(
            "recovery", f"Resuming operation {operation.operation_id}."
        )
        self._start_job(
            "recover",
            "recovery",
            lambda progress: self.engine.recover(
                operation.operation_id, progress=progress
            ),
        )

    def restore_selected(self) -> None:
        operation = self._selected_operation()
        if operation is None:
            return
        if not messagebox.askyesno(
            "Restore original path?",
            (
                f"Restore the recovery copy to:\n{operation.source}\n\n"
                "The moved destination will remain in place. Continue?"
            ),
            parent=self.root,
            default="no",
        ):
            return
        self._append_log(
            "recovery", f"Restoring recovery copy for {operation.operation_id}."
        )
        self._start_job(
            "restore",
            "recovery",
            lambda _progress: self.engine.restore_backup(operation.operation_id),
        )

    def purge_selected(self) -> None:
        operation = self._selected_operation()
        if operation is None:
            return
        confirmed = messagebox.askyesno(
            "Permanently purge recovery copy?",
            (
                f"Recovery copy:\n{operation.recovery_copy}\n\n"
                "Safe File Mover will re-verify the destination and recovery copy, "
                "then permanently delete the recovery copy. This cannot be undone.\n\n"
                "Close programs using either path first. File contents and Windows "
                "named data streams are verified, but filesystem ACL/ownership details "
                "remain outside the manifest.\n\n"
                "Continue?"
            ),
            parent=self.root,
            icon="warning",
            default="no",
        )
        if not confirmed:
            return
        remote_destination = is_remote_path(operation.destination)
        if remote_destination and not messagebox.askyesno(
            "Acknowledge remote-storage risk?",
            (
                "The destination is a network share. Safe File Mover can verify the "
                "bytes returned by the server, but it cannot prove that the server, "
                "controller, or provider has made them power-loss durable.\n\n"
                "Purge only after opening/validating the application data or confirming "
                "a provider-side snapshot. Permanently remove the recovery copy?"
            ),
            parent=self.root,
            icon="warning",
            default="no",
        ):
            return
        self._append_log(
            "recovery", f"Purging recovery copy for {operation.operation_id}."
        )
        self._start_job(
            "purge",
            "recovery",
            lambda _progress: self.engine.purge_backup(
                operation.operation_id,
                acknowledge_remote_risk=remote_destination,
            ),
        )

    def abandon_selected(self) -> None:
        operation = self._selected_operation()
        if operation is None:
            return
        if not messagebox.askyesno(
            "Abandon interrupted move?",
            (
                "Discard this operation's uncommitted staging data?\n\n"
                f"Operation: {operation.operation_id}\n"
                f"Source preserved at: {operation.source}\n\n"
                "The source is verified before staging data is removed."
            ),
            parent=self.root,
            icon="warning",
            default="no",
        ):
            return
        self._append_log("recovery", f"Abandoning {operation.operation_id}.")
        self._start_job(
            "abandon",
            "recovery",
            lambda _progress: self.engine.abandon(operation.operation_id),
        )

    def _selected_operation(self) -> MoveOperation | None:
        selected = self.operations_tree.selection()
        if not selected:
            messagebox.showinfo(
                "Select an operation",
                "Select an operation in the recovery table first.",
                parent=self.root,
            )
            return None
        operation = self._operations.get(selected[0])
        if operation is None:
            messagebox.showerror(
                "Operation unavailable",
                "The selected operation is no longer in the current list. Refresh and try again.",
                parent=self.root,
            )
        return operation

    def _start_job(
        self,
        action: str,
        tab: str,
        work: Worker,
        *,
        quiet: bool = False,
    ) -> None:
        if self._busy:
            if not quiet:
                messagebox.showinfo(
                    "Operation in progress",
                    "Wait for the current operation to finish before starting another.",
                    parent=self.root,
                )
            return
        self._busy = True
        self._set_busy_controls(True)
        self.app_status_var.set(f"{action.replace('_', ' ').title()} in progress…")
        self._prepare_progress(tab, action)

        def report(progress: Progress) -> None:
            self._events.put(("progress", action, tab, progress))

        def runner() -> None:
            try:
                result = work(report)
            except Exception as error:  # Keep the worker alive long enough to report it.
                self._events.put(
                    (
                        "error",
                        action,
                        tab,
                        type(error).__name__,
                        str(error) or repr(error),
                        traceback.format_exc(),
                    )
                )
            else:
                self._events.put(("result", action, tab, result))
            finally:
                self._events.put(("finished", action, tab))

        threading.Thread(
            target=runner,
            name=f"safe-file-mover-{action}",
            daemon=True,
        ).start()

    def _prepare_progress(self, tab: str, action: str) -> None:
        bar, label, path = self._progress_widgets(tab)
        bar.stop()
        bar.configure(mode="indeterminate", maximum=100, value=0)
        bar.start(12)
        label.set(f"{action.replace('_', ' ').title()}…")
        path.set("")

    def _poll_events(self) -> None:
        if self._closing:
            return
        try:
            while True:
                event = self._events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _kind, _action, tab, progress = event
                    self._show_progress(tab, progress)
                elif kind == "result":
                    _kind, action, tab, result = event
                    self._handle_result(action, tab, result)
                elif kind == "error":
                    _kind, action, tab, error_name, message, details = event
                    self._handle_error(
                        action, tab, error_name, message, details
                    )
                elif kind == "finished":
                    _kind, action, tab = event
                    self._finish_job(action, tab)
        except queue.Empty:
            pass
        self.root.after(self._POLL_INTERVAL_MS, self._poll_events)

    def _show_progress(self, tab: str, progress: Progress) -> None:
        bar, label, path = self._progress_widgets(tab)
        bar.stop()
        bar.configure(mode="determinate", maximum=100)
        if progress.total_bytes > 0:
            percentage = min(100.0, 100.0 * progress.bytes_done / progress.total_bytes)
            summary = f"{percentage:.1f}% · {_format_size(progress.bytes_done)} of {_format_size(progress.total_bytes)}"
            bar["value"] = percentage
        elif progress.item_count > 0:
            percentage = min(
                100.0, 100.0 * progress.items_done / progress.item_count
            )
            summary = f"{progress.items_done:,} of {progress.item_count:,} items"
            bar["value"] = percentage
        else:
            summary = "Working"
            bar["value"] = 0
        label.set(f"{progress.phase.replace('_', ' ').title()}: {summary}")
        path.set(progress.path)

    def _handle_result(self, action: str, tab: str, result: Any) -> None:
        if action == "preview" and isinstance(result, MovePlan):
            plan = result
            warnings = "\n".join(f"  • {warning}" for warning in plan.warnings)
            self._append_log(
                "move",
                (
                    "Preview complete; no files or journal records were changed.\n"
                    f"  Source: {plan.source}\n"
                    f"  Destination: {plan.destination}\n"
                    f"  Items: {plan.manifest.item_count:,} "
                    f"({plan.manifest.file_count:,} files, "
                    f"{plan.manifest.directory_count:,} folders)\n"
                    f"  Data: {_format_size(plan.manifest.total_bytes)}\n"
                    f"  Approximate space needed: {_format_size(plan.required_bytes)}\n"
                    f"  Free space: {_format_size(plan.free_bytes)}\n"
                    f"Warnings:\n{warnings}"
                ),
            )
            self.move_progress_var.set("Preview complete")
            self.move_progress_path_var.set(str(plan.destination))
            self.move_progress.configure(mode="determinate", value=100)
            return

        if action == "refresh" and isinstance(result, list):
            self._populate_operations(result)
            self.recovery_progress_var.set(
                f"Loaded {len(result):,} journaled operation"
                f"{'s' if len(result) != 1 else ''}"
            )
            self.recovery_progress_path_var.set("")
            self.recovery_progress.configure(mode="determinate", value=100)
            return

        if isinstance(result, MoveOperation):
            operation = result
            log_tab = "move" if action == "move" else "recovery"
            lines = [
                f"{action.title()} complete.",
                f"  Operation: {operation.operation_id}",
                f"  Status: {operation.status}",
                f"  Source: {operation.source}",
                f"  Destination: {operation.destination}",
                f"  Data: {_format_size(operation.total_bytes)} in {operation.item_count:,} items",
            ]
            if operation.status == "backup_retained":
                lines.append(f"  Recovery copy: {operation.recovery_copy}")
            if operation.last_error:
                lines.append(f"  Last error: {operation.last_error}")
            self._append_log(log_tab, "\n".join(lines))
            bar, label, path = self._progress_widgets(log_tab)
            bar.stop()
            bar.configure(mode="determinate", value=100)
            label.set(f"{action.title()} complete: {operation.status}")
            path.set(str(operation.destination))
            self._refresh_after_job = True

    def _handle_error(
        self,
        action: str,
        tab: str,
        error_name: str,
        message: str,
        details: str,
    ) -> None:
        self._append_log(
            tab,
            f"{action.title()} failed: {error_name}: {message}\n{details.rstrip()}",
        )
        bar, label, path = self._progress_widgets(tab)
        bar.stop()
        bar.configure(mode="determinate", value=0)
        label.set(f"{action.title()} failed")
        path.set(message)
        self._refresh_after_job = action not in {"preview", "refresh"}
        messagebox.showerror(
            f"{action.title()} failed",
            (
                f"{message}\n\n"
                "No existing destination was overwritten. If the move was interrupted, "
                "use the Recovery tab after resolving the problem."
            ),
            parent=self.root,
        )

    def _finish_job(self, action: str, tab: str) -> None:
        bar, _label, _path = self._progress_widgets(tab)
        bar.stop()
        self._busy = False
        self._set_busy_controls(False)
        self.app_status_var.set("Ready")
        if self._refresh_after_job:
            self._refresh_after_job = False
            self.root.after_idle(self.refresh_operations)

    def _set_busy_controls(self, busy: bool) -> None:
        if busy:
            for button in (
                self.preview_button,
                self.move_button,
                self.refresh_button,
                self.recover_button,
                self.restore_button,
                self.purge_button,
                self.abandon_button,
            ):
                button.state(["disabled"])
        else:
            self.preview_button.state(["!disabled"])
            self.move_button.state(["!disabled"])
            self.refresh_button.state(["!disabled"])
            self._update_recovery_buttons()

    def _populate_operations(self, operations: list[MoveOperation]) -> None:
        previous = self.operations_tree.selection()
        previous_id = previous[0] if previous else None
        self._operations = {operation.operation_id: operation for operation in operations}
        for item in self.operations_tree.get_children():
            self.operations_tree.delete(item)
        for operation in operations:
            if operation.last_error:
                tag = "failed"
            elif operation.status in RECOVERABLE_STATUSES:
                tag = "attention"
            elif operation.status == "backup_retained":
                tag = "retained"
            else:
                tag = ""
            self.operations_tree.insert(
                "",
                "end",
                iid=operation.operation_id,
                values=(
                    operation.operation_id,
                    operation.status.replace("_", " "),
                    str(operation.source),
                    str(operation.destination),
                    _format_size(operation.total_bytes),
                    str(operation.recovery_copy)
                    if operation.status == "backup_retained"
                    else "",
                ),
                tags=(tag,) if tag else (),
            )
        if previous_id in self._operations:
            self.operations_tree.selection_set(previous_id)
            self.operations_tree.focus(previous_id)
            self.operations_tree.see(previous_id)
        elif operations:
            first = operations[0].operation_id
            self.operations_tree.selection_set(first)
            self.operations_tree.focus(first)
        else:
            self.operation_detail_var.set("No journaled operations to display.")
        self._on_operation_selected()

    def _on_operation_selected(self, _event: tk.Event[Any] | None = None) -> None:
        selected = self.operations_tree.selection()
        operation = self._operations.get(selected[0]) if selected else None
        if operation is None:
            if self._operations:
                self.operation_detail_var.set(
                    "Select an operation to see its paths and available actions."
                )
            self._update_recovery_buttons()
            return
        details = (
            f"Source: {operation.source}\n"
            f"Destination: {operation.destination}\n"
            f"Recorded recovery path: {operation.recovery_copy}"
        )
        if operation.last_error:
            details += f"\nLast error: {operation.last_error}"
        self.operation_detail_var.set(details)
        self._update_recovery_buttons()

    def _update_recovery_buttons(self) -> None:
        selected = self.operations_tree.selection()
        operation = self._operations.get(selected[0]) if selected else None
        status = operation.status if operation is not None else ""
        enabled = not self._busy
        self._set_button_state(
            self.recover_button, enabled and status in RECOVERABLE_STATUSES
        )
        self._set_button_state(
            self.restore_button, enabled and status == "backup_retained"
        )
        self._set_button_state(
            self.purge_button, enabled and status == "backup_retained"
        )
        self._set_button_state(
            self.abandon_button, enabled and status in ABANDONABLE_STATUSES
        )

    @staticmethod
    def _set_button_state(button: ttk.Button, enabled: bool) -> None:
        button.state(["!disabled"] if enabled else ["disabled"])

    def _progress_widgets(
        self, tab: str
    ) -> tuple[ttk.Progressbar, tk.StringVar, tk.StringVar]:
        if tab == "move":
            return (
                self.move_progress,
                self.move_progress_var,
                self.move_progress_path_var,
            )
        return (
            self.recovery_progress,
            self.recovery_progress_var,
            self.recovery_progress_path_var,
        )

    def _append_log(self, tab: str, message: str) -> None:
        widget = self.move_log if tab == "move" else self.recovery_log
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        widget.configure(state="normal")
        widget.insert("end", f"[{timestamp}] {message.rstrip()}\n\n")
        widget.configure(state="disabled")
        widget.see("end")

    def _on_close(self) -> None:
        if self._busy:
            messagebox.showwarning(
                "Operation still running",
                (
                    "Wait for the current operation to finish before closing. "
                    "If the process is forcibly stopped, reopen the app and use the "
                    "Recovery tab."
                ),
                parent=self.root,
            )
            return
        self._closing = True
        self.root.destroy()


def _format_size(size: int) -> str:
    value = float(size)
    units = ("bytes", "KiB", "MiB", "GiB", "TiB", "PiB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{value:,.0f} {unit}"
            return f"{value:,.2f} {unit}"
        value /= 1024
    return f"{size:,} bytes"


def launch(state_directory: Path | str | None = None) -> None:
    """Create the Tk application and run it until the window is closed."""

    root = tk.Tk()
    try:
        app = SafeFileMoverApp(root, state_directory=state_directory)
    except (SafeMoveError, OSError, ValueError) as error:
        messagebox.showerror(
            "Safe File Mover could not start",
            str(error),
            parent=root,
        )
        root.destroy()
        return
    root.mainloop()
    del app


__all__ = ["SafeFileMoverApp", "launch"]
