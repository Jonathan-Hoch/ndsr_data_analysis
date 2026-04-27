# NDSR Folder Workflow

Simple tools for combining NDSR raw text exports into one master CSV, then choosing columns to view, average, and export.

This workflow was built for folders that contain many study subfolders, where each subfolder contains NDSR `.txt` exports and the files of interest have names ending in `4` such as `IMST2804.txt` or `XS2104.txt`.

## What This Does

This workflow has two steps:

1. Build one master CSV from a folder of NDSR subfolders.
2. Open that master CSV in a simple GUI where you can:
   - choose which columns to display
   - filter by project or participant
   - switch between individual rows and averaged output
   - export the selected view to a new CSV

## Files

- `build_ndsr_master.py`
  Builds the master CSV from a folder of NDSR text files.
- `ndsr_master_gui.py`
  Opens the master CSV in a point-and-click viewer/export tool.
- `ndsr_master_backend.py`
  Shared backend logic used by the other two scripts.

## Before You Start

You need:

- Windows
- Python installed

To check whether Python is installed, open PowerShell and run:

```powershell
python --version
```

If that prints a version number, you are ready.

## Folder Setup

Your folder should look something like this:

```text
A_Raw Files/
  IMST28d/
    IMST2804.txt
  IMST30d/
    IMST3004.txt
    IMST3014.txt
  XS21d/
    XS2104.txt
    XS2114.txt
  build_ndsr_master.py
  ndsr_master_gui.py
  ndsr_master_backend.py
```

The builder searches for `.txt` files whose filename stem ends in `4`.

## Step 1: Build the Master CSV

Open PowerShell in the folder that contains the scripts, then run:

```powershell
python build_ndsr_master.py --pick-folder
```

What happens:

- a folder picker opens
- you choose the folder that contains all of the study folders
- the script combines the matching files into one CSV
- it writes `master_ndsr_combined.csv`

If you prefer not to use the folder picker, you can also run:

```powershell
python build_ndsr_master.py .
```

## Step 2: Open the GUI

After the master CSV has been created, run:

```powershell
python ndsr_master_gui.py master_ndsr_combined.csv
```

This opens a window where you can:

- search and select columns
- filter projects
- filter participants
- switch between:
  - `Individual rows`
  - `Average`
- export the current preview as a CSV

## Typical Workflow

1. Run:

```powershell
python build_ndsr_master.py --pick-folder
```

2. Run:

```powershell
python ndsr_master_gui.py master_ndsr_combined.csv
```

3. In the GUI:
   - select the columns you want
   - choose `Individual rows` or `Average`
   - click `Export Preview CSV`

## Notes About Averaging

In Average mode, the program can group by:

- `Participant ID Root`
- `Participant ID`
- `Project Abbreviation`

Numeric columns are averaged.

Text columns are handled carefully:

- if all values in the group are the same, that value is kept
- if text values differ, the cell is left blank instead of guessing

This is intentional.

## Important Data Note

The master CSV keeps the union of all columns across matching files.

That matters because some files ending in `14` are supplement exports and may have different columns from files ending in `04`.

The combined master file keeps:

- all matched rows
- all discovered columns
- `Source Folder`
- `Source File`

This makes it possible to trace rows back to their original file.

## Troubleshooting

### Nothing happens when running Python

Try:

```powershell
py --version
```

If `py` works but `python` does not, use `py` instead of `python` in the commands.

Example:

```powershell
py build_ndsr_master.py --pick-folder
py ndsr_master_gui.py master_ndsr_combined.csv
```

### The GUI does not open

That usually means Python was installed without the needed Windows GUI components, or the local Python install is incomplete.

### The master CSV is missing rows you expected

This workflow only includes `.txt` files whose filename stem ends in `4`.

## Suggested GitHub Use

If you share this on GitHub, it is best to upload:

- `build_ndsr_master.py`
- `ndsr_master_gui.py`
- `ndsr_master_backend.py`
- `README.md`

It is usually best **not** to upload:

- participant raw data folders
- generated CSV files
- any sensitive or identifying data

## Copy-Paste Commands

Build the master CSV:

```powershell
python build_ndsr_master.py --pick-folder
```

Open the GUI:

```powershell
python ndsr_master_gui.py master_ndsr_combined.csv
```
