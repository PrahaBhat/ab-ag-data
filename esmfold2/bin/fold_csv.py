#!/usr/bin/env python3
"""Run ESMFold2 on records from abag_foldable_constructs_v3.csv."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tqdm import tqdm

from abag_fold.csv_input import filter_rows, iter_csv_rows  # noqa: E402
from abag_fold.guardrails import FoldPlan, SkipRecord  # noqa: E402
from abag_fold.runner import (  # noqa: E402
    ESMFold2Runner,
    append_jsonl,
    load_config,
    merge_config,
    plan_from_row,
    skip_to_dict,
    write_result,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fold abag CSV with ESMFold2")
    parser.add_argument("--csv", type=Path, help="Path to CSV")
    parser.add_argument("--config", type=Path, default=ROOT / "config.defaults.yaml")
    parser.add_argument("--config-local", type=Path, default=ROOT / "config.local.yaml")
    parser.add_argument("--output-dir", type=Path, help="Per-record PDB output directory")
    parser.add_argument("--manifest-only", type=Path, help="Only fold record_ids marked ok in this JSONL")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--record-id", action="append", default=[], dest="record_ids")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not load model")
    args = parser.parse_args()

    cfg = load_config(args.config)
    local_path = args.config_local
    if local_path.is_file():
        cfg = merge_config(cfg, load_config(local_path))

    csv_path = args.csv or (ROOT / cfg["csv_path"]).resolve()
    out_dir = args.output_dir or (ROOT / cfg.get("output_dir", "./outputs")).resolve()
    log_path = out_dir / "fold_log.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)

    allowed_ids: set[str] | None = None
    if args.manifest_only:
        allowed_ids = set()
        with args.manifest_only.open() as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("status") == "ok":
                    allowed_ids.add(rec["record_id"])

    record_filter = set(args.record_ids) if args.record_ids else allowed_ids
    rows = list(
        filter_rows(
            iter_csv_rows(csv_path),
            record_ids=record_filter,
            offset=args.offset,
            limit=args.limit,
        )
    )

    runner: ESMFold2Runner | None = None
    if not args.dry_run:
        runner = ESMFold2Runner(cfg.get("model_id", "biohub/ESMFold2-hf"))
        print(f"Loading {runner.model_id} …")
        runner.load()

    folded = skipped = 0
    for row in tqdm(rows, desc="records"):
        result = plan_from_row(row, cfg)
        if isinstance(result, SkipRecord):
            skipped += 1
            append_jsonl(log_path, {"status": "skip", **skip_to_dict(result)})
            continue

        plan: FoldPlan = result
        pdb_path = out_dir / plan.record_id / f"{plan.record_id}.pdb"
        if args.skip_existing and pdb_path.is_file():
            append_jsonl(log_path, {"status": "skip", "record_id": plan.record_id, "reason": "exists"})
            continue

        if args.dry_run:
            append_jsonl(
                log_path,
                {
                    "status": "dry_run_ok",
                    "record_id": plan.record_id,
                    "total_length": plan.total_length,
                    "chain_lengths": plan.chain_lengths,
                },
            )
            folded += 1
            continue

        assert runner is not None
        fold_result = runner.fold_plan(plan, cfg)
        write_result(out_dir, plan, fold_result)
        append_jsonl(
            log_path,
            {"status": "folded", "record_id": plan.record_id, "metrics": fold_result.get("metrics")},
        )
        folded += 1

    print(f"Done. folded/dry_ok={folded} skipped={skipped} log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
