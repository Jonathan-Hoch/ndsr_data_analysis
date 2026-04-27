from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from ndsr_master_backend import (
    ValidationError,
    average_group_label,
    average_records,
    load_master_csv,
    value_to_text,
    write_csv,
)


DEFAULT_COLUMNS = [
    "Project Abbreviation",
    "Participant ID",
    "Date of Intake",
    "Total Dietary Fiber (g)",
    "Sodium (mg)",
]

AVERAGE_GROUP_LABELS = (
    "Participant ID Root",
    "Participant ID",
    "Project Abbreviation",
)


class MasterGui:
    def __init__(self, root: tk.Tk, initial_csv: Path | None = None) -> None:
        self.root = root
        self.root.title("NDSR Master CSV Viewer")
        self.root.geometry("1500x920")

        self.csv_var = tk.StringVar(value=str(initial_csv.resolve()) if initial_csv else "")
        self.status_var = tk.StringVar(value="Load a master CSV to begin.")
        self.project_search_var = tk.StringVar()
        self.participant_search_var = tk.StringVar()
        self.column_search_var = tk.StringVar()
        self.view_mode_var = tk.StringVar(value="individual")
        self.average_group_var = tk.StringVar(value="Participant ID Root")

        self.records: list[dict[str, Any]] = []
        self.headers: list[str] = []
        self.project_values: list[str] = []
        self.participant_values: list[str] = []
        self.displayed_projects: list[str] = []
        self.displayed_participants: list[str] = []
        self.displayed_columns: list[str] = []
        self.current_preview_records: list[dict[str, Any]] = []
        self.sort_column: str | None = None
        self.sort_reverse = False

        self._build_ui()
        self._bind_events()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        csv_frame = ttk.LabelFrame(outer, text="Master CSV", padding=10)
        csv_frame.grid(row=0, column=0, sticky="ew")
        csv_frame.columnconfigure(0, weight=1)

        ttk.Entry(csv_frame, textvariable=self.csv_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(csv_frame, text="Browse", command=self.browse_csv).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(csv_frame, text="Load CSV", command=self.load_csv).grid(row=0, column=2)

        mode_frame = ttk.LabelFrame(outer, text="View", padding=10)
        mode_frame.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        ttk.Radiobutton(
            mode_frame,
            text="Individual rows",
            variable=self.view_mode_var,
            value="individual",
            command=self.refresh_preview,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            mode_frame,
            text="Average",
            variable=self.view_mode_var,
            value="average",
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Label(mode_frame, text="Average using:").pack(side="left", padx=(20, 8))
        average_group_box = ttk.Combobox(
            mode_frame,
            textvariable=self.average_group_var,
            values=AVERAGE_GROUP_LABELS,
            state="readonly",
            width=22,
        )
        average_group_box.pack(side="left")
        average_group_box.bind("<<ComboboxSelected>>", lambda _: self.refresh_preview())

        selectors_frame = ttk.Frame(outer)
        selectors_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        selectors_frame.columnconfigure(0, weight=1)
        selectors_frame.columnconfigure(1, weight=1)
        selectors_frame.columnconfigure(2, weight=2)

        self._build_selector_panel(selectors_frame, 0, "Projects", self.project_search_var, "project_listbox")
        self._build_selector_panel(selectors_frame, 1, "Participants", self.participant_search_var, "participant_listbox")
        self._build_selector_panel(selectors_frame, 2, "Columns", self.column_search_var, "column_listbox")

        preview_frame = ttk.LabelFrame(outer, text="Preview", padding=10)
        preview_frame.grid(row=3, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(preview_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        footer = ttk.Frame(outer)
        footer.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(1, weight=1)

        actions = ttk.Frame(footer)
        actions.grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Reset Filters", command=self.reset_filters).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Select Default Columns", command=self.select_default_columns).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Copy Preview", command=self.copy_preview).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Export Preview CSV", command=self.export_preview_csv).pack(side="left")

        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

    def _build_selector_panel(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        search_var: tk.StringVar,
        assign_listbox: str,
    ) -> None:
        panel = ttk.LabelFrame(parent, text=title, padding=8)
        panel.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Entry(panel, textvariable=search_var).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        listbox = tk.Listbox(panel, selectmode=tk.EXTENDED, exportselection=False)
        listbox.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        listbox.configure(yscrollcommand=scrollbar.set)
        setattr(self, assign_listbox, listbox)

    def _bind_events(self) -> None:
        self.project_search_var.trace_add("write", lambda *_: self.refresh_project_list())
        self.participant_search_var.trace_add("write", lambda *_: self.refresh_participant_list())
        self.column_search_var.trace_add("write", lambda *_: self.refresh_column_list())
        self.project_listbox.bind("<<ListboxSelect>>", lambda _: self.on_project_selection_changed())
        self.participant_listbox.bind("<<ListboxSelect>>", lambda _: self.refresh_preview())
        self.column_listbox.bind("<<ListboxSelect>>", lambda _: self.refresh_preview())

    def browse_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select master CSV", filetypes=[("CSV file", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_var.set(path)

    def load_csv(self) -> None:
        csv_path = Path(self.csv_var.get().strip())
        if not csv_path.exists():
            messagebox.showerror("CSV not found", f"Could not find:\n{csv_path}")
            return

        try:
            records, headers = load_master_csv(csv_path)
        except ValidationError as exc:
            messagebox.showerror("Validation error", str(exc))
            self.status_var.set("Load failed.")
            return
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            self.status_var.set("Load failed.")
            return

        self.records = records
        self.headers = headers
        self.project_values = sorted(
            {
                value_to_text(record.get("Project Abbreviation"))
                for record in self.records
                if value_to_text(record.get("Project Abbreviation"))
            }
        )
        self.refresh_project_list(keep_selection=False)
        self.refresh_participant_list(keep_selection=False)
        self.refresh_column_list(keep_selection=False)
        self.select_default_columns()
        self.status_var.set(f"Loaded {len(self.records)} rows from {csv_path.name}.")

    def reset_filters(self) -> None:
        self.project_search_var.set("")
        self.participant_search_var.set("")
        self.column_search_var.set("")
        if self.project_listbox.size():
            self.project_listbox.selection_clear(0, tk.END)
        if self.participant_listbox.size():
            self.participant_listbox.selection_clear(0, tk.END)
        self.refresh_project_list()
        self.refresh_participant_list()
        self.refresh_column_list()
        self.select_default_columns()

    def selected_values(self, listbox: tk.Listbox, displayed_values: list[str]) -> list[str]:
        return [displayed_values[i] for i in listbox.curselection() if i < len(displayed_values)]

    def set_listbox_items(self, listbox: tk.Listbox, items: list[str], previous_selection: set[str]) -> None:
        listbox.delete(0, tk.END)
        for item in items:
            listbox.insert(tk.END, item)
        for idx, item in enumerate(items):
            if item in previous_selection:
                listbox.selection_set(idx)

    def refresh_project_list(self, keep_selection: bool = True) -> None:
        previous = set(self.selected_values(self.project_listbox, self.displayed_projects)) if keep_selection else set()
        search = self.project_search_var.get().strip().lower()
        self.displayed_projects = [value for value in self.project_values if search in value.lower()]
        self.set_listbox_items(self.project_listbox, self.displayed_projects, previous)
        self.refresh_participant_list()

    def refresh_participant_list(self, keep_selection: bool = True) -> None:
        previous = set(self.selected_values(self.participant_listbox, self.displayed_participants)) if keep_selection else set()
        project_selection = set(self.selected_values(self.project_listbox, self.displayed_projects))
        scoped_records = self.records
        if project_selection:
            scoped_records = [
                record
                for record in self.records
                if value_to_text(record.get("Project Abbreviation")) in project_selection
            ]
        participants = sorted(
            {
                value_to_text(record.get("Participant ID"))
                for record in scoped_records
                if value_to_text(record.get("Participant ID"))
            }
        )
        search = self.participant_search_var.get().strip().lower()
        self.participant_values = participants
        self.displayed_participants = [value for value in participants if search in value.lower()]
        self.set_listbox_items(self.participant_listbox, self.displayed_participants, previous)
        self.refresh_preview()

    def refresh_column_list(self, keep_selection: bool = True) -> None:
        previous = set(self.selected_values(self.column_listbox, self.displayed_columns)) if keep_selection else set()
        search = self.column_search_var.get().strip().lower()
        self.displayed_columns = [header for header in self.headers if search in header.lower()]
        self.set_listbox_items(self.column_listbox, self.displayed_columns, previous)
        self.refresh_preview()

    def on_project_selection_changed(self) -> None:
        self.refresh_participant_list()

    def get_filtered_records(self) -> list[dict[str, Any]]:
        project_selection = set(self.selected_values(self.project_listbox, self.displayed_projects))
        participant_selection = set(self.selected_values(self.participant_listbox, self.displayed_participants))

        filtered = self.records
        if project_selection:
            filtered = [
                record
                for record in filtered
                if value_to_text(record.get("Project Abbreviation")) in project_selection
            ]
        if participant_selection:
            filtered = [
                record
                for record in filtered
                if value_to_text(record.get("Participant ID")) in participant_selection
            ]
        return filtered

    def get_selected_columns(self) -> list[str]:
        columns = self.selected_values(self.column_listbox, self.displayed_columns)
        if not columns:
            columns = [header for header in DEFAULT_COLUMNS if header in self.headers]
        if self.view_mode_var.get() == "average":
            group_label = average_group_label(self.average_group_var.get())
            columns = [group_label, "Record Count"] + [column for column in columns if column != group_label]
        return columns

    def refresh_preview(self) -> None:
        if not self.records or not self.headers:
            return

        columns = self.get_selected_columns()
        records = self.get_preview_records(columns)
        if self.sort_column and self.sort_column in columns:
            records = sorted(records, key=lambda record: value_to_text(record.get(self.sort_column)), reverse=self.sort_reverse)

        self.current_preview_records = records
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns

        for column in columns:
            self.tree.heading(column, text=column, command=lambda c=column: self.sort_by(c))
            self.tree.column(column, width=self.initial_width(column), stretch=True, anchor="w")

        for record in records:
            self.tree.insert("", tk.END, values=[value_to_text(record.get(column)) for column in columns])

        self.status_var.set(
            f"{len(records)} rows shown | {len(columns)} columns | mode: "
            f"{'average' if self.view_mode_var.get() == 'average' else 'individual'}"
        )

    def get_preview_records(self, columns: list[str]) -> list[dict[str, Any]]:
        filtered = self.get_filtered_records()
        if self.view_mode_var.get() != "average":
            return [{column: record.get(column, "") for column in columns} for record in filtered]
        return average_records(filtered, columns, mode=self.average_group_var.get())

    def initial_width(self, column: str) -> int:
        if column in {"Project Abbreviation", "Participant ID", "Participant ID Root", "Source Folder", "Source File"}:
            return 140
        if "Date" in column:
            return 140
        return 180

    def sort_by(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.refresh_preview()

    def select_default_columns(self) -> None:
        desired = [header for header in DEFAULT_COLUMNS if header in self.displayed_columns]
        self.column_listbox.selection_clear(0, tk.END)
        for idx, header in enumerate(self.displayed_columns):
            if header in desired:
                self.column_listbox.selection_set(idx)
        self.refresh_preview()

    def copy_preview(self) -> None:
        if not self.current_preview_records:
            messagebox.showinfo("Nothing to copy", "No preview rows are currently visible.")
            return
        columns = self.get_selected_columns()
        lines = ["\t".join(columns)]
        lines.extend("\t".join(value_to_text(record.get(column)) for column in columns) for record in self.current_preview_records)
        payload = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self.root.update()
        self.status_var.set(f"Copied {len(self.current_preview_records)} rows to the clipboard.")

    def export_preview_csv(self) -> None:
        if not self.current_preview_records:
            messagebox.showinfo("Nothing to export", "No preview rows are currently visible.")
            return
        path = filedialog.asksaveasfilename(
            title="Save preview CSV",
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
            initialfile="ndsr_selected_output.csv",
        )
        if not path:
            return
        columns = self.get_selected_columns()
        write_csv(Path(path), columns, self.current_preview_records)
        self.status_var.set(f"Exported {len(self.current_preview_records)} preview rows to {path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a master NDSR CSV and preview individual or averaged outputs.")
    parser.add_argument("csv", nargs="?", default="", help="Optional master CSV path to load on startup.")
    args = parser.parse_args()

    root = tk.Tk()
    app = MasterGui(root, initial_csv=Path(args.csv) if args.csv else None)
    if args.csv and Path(args.csv).exists():
        app.load_csv()
    root.mainloop()


if __name__ == "__main__":
    main()
