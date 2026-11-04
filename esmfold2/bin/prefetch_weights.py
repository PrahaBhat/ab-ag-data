#!/usr/bin/env python3
"""Download ESMFold2 weights into the repo-local Hugging Face cache."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-id",
        default=os.environ.get("ESMFOLD2_MODEL_ID", "biohub/ESMFold2-hf"),
    )
    args = parser.parse_args()

    # env.sh should set HF_HOME before this runs
    hf_home = os.environ.get("HF_HOME", ROOT / "cache" / "huggingface")
    print(f"HF_HOME={hf_home}")
    print(f"Prefetching {args.model_id} …")

    from transformers import EsmFold2Model

    EsmFold2Model.from_pretrained(args.model_id)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
