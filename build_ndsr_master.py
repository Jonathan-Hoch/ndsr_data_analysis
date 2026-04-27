from __future__ import annotations

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from ndsr_master_backend import load_folder_records, write_csv


def choose_folder(initial_dir: str | None = None) -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(
            title="Select folder containing NDSR study folders",
            initialdir=initial_dir or str(Path(".").resolve()),
        )
    finally:
        root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a master CSV from NDSR text files whose basenames end in '4'."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Folder containing study subfolders or raw NDSR text files. Defaults to the current folder.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="master_ndsr_combined.csv",
        help="Output CSV path. Defaults to master_ndsr_combined.csv.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not search subfolders recursively.",
    )
    parser.add_argument(
        "--pick-folder",
        action="store_true",
        help="Open a folder picker instead of typing the source folder path.",
    )
    args = parser.parse_args()

    source_folder = args.folder
    if args.pick_folder:
        picked = choose_folder(initial_dir=args.folder)
        if not picked:
            print("No folder selected. Exiting.")
            return
        source_folder = picked

    records, headers = load_folder_records(source_folder, recursive=not args.no_recursive)
    output_path = Path(args.output).resolve()
    write_csv(output_path, headers, records)
    print(f"Wrote {len(records)} rows and {len(headers)} columns to {output_path}")


if __name__ == "__main__":
    main()
