from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from abag_fold.constants import CSV_COLUMNS


def iter_csv_rows(csv_path: Path) -> Iterator[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"No header in {csv_path}")
        missing = [c for c in CSV_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{csv_path} missing columns: {missing}")
        yield from reader


def filter_rows(
    rows: Iterator[dict[str, str]],
    *,
    record_ids: set[str] | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> Iterator[dict[str, str]]:
    skipped = 0
    taken = 0
    for row in rows:
        rid = (row.get("record_id") or "").strip()
        if record_ids is not None and rid not in record_ids:
            continue
        if skipped < offset:
            skipped += 1
            continue
        if limit is not None and taken >= limit:
            break
        taken += 1
        yield row
