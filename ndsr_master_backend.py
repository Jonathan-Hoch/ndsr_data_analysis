from __future__ import annotations

import csv
import re
from pathlib import Path
from statistics import mean
from typing import Any


class ValidationError(RuntimeError):
    """Raised when input files are missing required structure."""


def normalize_fieldnames(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        raise ValidationError("Input file is missing a header row.")
    return [name.strip() for name in fieldnames]


def find_matching_files(folder: Path, recursive: bool = True) -> list[Path]:
    pattern = "**/*.txt" if recursive else "*.txt"
    return sorted(path for path in folder.glob(pattern) if path.is_file() and path.stem.endswith("4"))


def load_folder_records(folder: str | Path, recursive: bool = True) -> tuple[list[dict[str, str]], list[str]]:
    folder = Path(folder)
    matched_files = find_matching_files(folder, recursive=recursive)
    if not matched_files:
        raise ValidationError(f"No .txt files ending in '4' were found in {folder}")

    records: list[dict[str, str]] = []
    headers: list[str] = ["Participant ID", "Source Folder", "Source File"]

    for path in matched_files:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            current_headers = normalize_fieldnames(reader.fieldnames)
            reader.fieldnames = current_headers

            if "Participant ID" not in current_headers:
                raise ValidationError(f"'Participant ID' column not found in {path}")

            for header in current_headers:
                if header not in headers:
                    headers.append(header)

            for row in reader:
                cleaned = {key.strip(): (value or "").strip() for key, value in row.items()}
                if not any(cleaned.values()):
                    continue
                cleaned["Source Folder"] = path.parent.name
                cleaned["Source File"] = path.name
                records.append(cleaned)

    return records, headers


def load_master_csv(path: str | Path) -> tuple[list[dict[str, str]], list[str]]:
    path = Path(path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = normalize_fieldnames(reader.fieldnames)
        reader.fieldnames = headers
        records = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    if "Participant ID" not in headers:
        raise ValidationError(f"'Participant ID' column not found in {path}")
    return records, headers


def write_csv(path: Path, fieldnames: list[str], records: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fieldnames})


def value_to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def parse_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = value_to_text(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def participant_id_root(value: Any) -> str:
    text = value_to_text(value).strip()
    if not text:
        return ""
    match = re.match(r"^(.*?)([-_ ]\d+)$", text)
    if match:
        return match.group(1).strip()
    return text


def average_group_label(mode: str) -> str:
    if mode == "Participant ID":
        return "Participant ID"
    if mode == "Project Abbreviation":
        return "Project Abbreviation"
    return "Participant ID Root"


def average_group_value(record: dict[str, Any], mode: str) -> str:
    if mode == "Participant ID":
        return value_to_text(record.get("Participant ID"))
    if mode == "Project Abbreviation":
        return value_to_text(record.get("Project Abbreviation"))
    return participant_id_root(record.get("Participant ID"))


def average_records(
    records: list[dict[str, Any]],
    columns: list[str],
    mode: str = "Participant ID Root",
) -> list[dict[str, Any]]:
    group_label = average_group_label(mode)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(average_group_value(record, mode), []).append(record)

    averaged_rows: list[dict[str, Any]] = []
    for group_value, group_rows in grouped.items():
        averaged: dict[str, Any] = {
            group_label: group_value,
            "Record Count": len(group_rows),
        }
        for column in columns:
            if column in {group_label, "Record Count"}:
                continue
            raw_values = [row.get(column, "") for row in group_rows]
            nonblank_values = [value for value in raw_values if value_to_text(value).strip()]
            numeric_values = [value for value in (parse_numeric(v) for v in raw_values) if value is not None]

            if numeric_values and len(numeric_values) == len(nonblank_values):
                averaged[column] = round(mean(numeric_values), 6)
                continue

            unique_text = sorted({value_to_text(value) for value in nonblank_values if value_to_text(value)})
            if len(unique_text) == 1:
                averaged[column] = unique_text[0]
            elif column == "Participant ID":
                averaged[column] = "; ".join(unique_text)
            else:
                averaged[column] = ""
        averaged_rows.append(averaged)
    return averaged_rows
