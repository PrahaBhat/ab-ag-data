#!/usr/bin/env python3
"""Dry-run: classify CSV rows as foldable or skipped (no GPU)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from abag_fold.csv_input import filter_rows, iter_csv_rows  # noqa: E402
from abag_fold.guardrails import FoldPlan, SkipRecord  # noqa: E402
from abag_fold.runner import load_config, merge_config, plan_from_row, skip_to_dict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build fold manifest from abag CSV")
    parser.add_argument("--csv", type=Path, help="Path to abag_foldable_constructs_v3.csv")
    parser.add_argument("--config", type=Path, default=ROOT / "config.defaults.yaml")
    parser.add_argument("--config-local", type=Path, default=ROOT / "config.local.yaml")
    parser.add_argument("--output", type=Path, help="JSONL manifest path")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--record-id", action="append", default=[], dest="record_ids")
    args = parser.parse_args()

    cfg = load_config(args.config)
    local_path = args.config_local
    if local_path.is_file():
        cfg = merge_config(cfg, load_config(local_path))

    csv_path = args.csv or (ROOT / cfg["csv_path"]).resolve()
    out_path = args.output or (ROOT / cfg.get("manifest_dir", "./manifests") / "manifest.jsonl").resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    record_filter = set(args.record_ids) if args.record_ids else None
    rows = filter_rows(
        iter_csv_rows(csv_path),
        record_ids=record_filter,
        offset=args.offset,
        limit=args.limit,
    )

    ok = skip = 0
    with out_path.open("w") as out_f:
        for row in rows:
            result = plan_from_row(row, cfg)
            if isinstance(result, SkipRecord):
                skip += 1
                out_f.write(json.dumps({"status": "skip", **skip_to_dict(result)}) + "\n")
            else:
                ok += 1
                plan: FoldPlan = result
                out_f.write(
                    json.dumps(
                        {
                            "status": "ok",
                            "record_id": plan.record_id,
                            "construct_type": plan.construct_type,
                            "fold_mode": plan.fold_mode,
                            "total_length": plan.total_length,
                            "chain_lengths": plan.chain_lengths,
                            "warnings": plan.warnings,
                        }
                    )
                    + "\n"
                )

    print(f"CSV: {csv_path}")
    print(f"Manifest: {out_path}")
    print(f"foldable: {ok}  skipped: {skip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
