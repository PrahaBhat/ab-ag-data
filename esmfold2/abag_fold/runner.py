from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from abag_fold.guardrails import FoldPlan, SkipRecord, build_fold_plan, pick_diffusion_samples


def load_config(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


def merge_config(defaults: dict, local: dict | None) -> dict:
    out = dict(defaults)
    if local:
        out.update(local)
    return out


class ESMFold2Runner:
    def __init__(
        self,
        model_id: str,
        *,
        use_kernels: bool = True,
        dtype=None,
    ):
        self.model_id = model_id
        self.use_kernels = use_kernels
        self.dtype = dtype
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import EsmFold2Model

        dtype = self.dtype if self.dtype is not None else torch.bfloat16
        self._model = EsmFold2Model.from_pretrained(
            self.model_id,
            dtype=dtype,
            device_map="auto",
            use_kernels=self.use_kernels,
        )

    @property
    def model(self):
        if self._model is None:
            raise RuntimeError("Call load() before folding")
        return self._model

    def fold_plan(self, plan: FoldPlan, config: dict) -> dict[str, Any]:
        import torch
        from transformers.models.esmfold2.protein_utils import output_to_pdb

        from abag_fold.multimer import prepare_multimer_features

        torch.manual_seed(int(config.get("seed", 42)))
        sequences = [c.sequence for c in plan.chains]
        samples = pick_diffusion_samples(
            plan.total_length,
            config.get("diffusion_samples_by_length") or [],
            int(config.get("num_diffusion_samples", 8)),
        )

        if len(sequences) == 1:
            pdb = self.model.infer_protein_as_pdb(sequences[0], num_diffusion_samples=samples)
            metrics = {"num_diffusion_samples": samples, "single_chain": True}
            return {"pdb": pdb, "metrics": metrics}

        features = prepare_multimer_features(sequences, device=self.model.device)
        output = self.model.fold(**features, num_diffusion_samples=samples)
        pdb = output_to_pdb(output, features)
        best = int(output.ptm.argmax()) if output.ptm is not None else 0
        metrics = {
            "num_diffusion_samples": samples,
            "single_chain": False,
            "ptm": float(output.ptm[best]) if output.ptm is not None else None,
            "iptm": float(output.iptm[best]) if output.iptm is not None else None,
            "complex_plddt": float(output.complex_plddt[best])
            if output.complex_plddt is not None
            else None,
        }
        return {"pdb": pdb, "metrics": metrics}


def write_result(out_dir: Path, plan: FoldPlan, fold_result: dict) -> None:
    rec_dir = out_dir / plan.record_id
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / f"{plan.record_id}.pdb").write_text(fold_result["pdb"])
    meta = {
        "record_id": plan.record_id,
        "construct_type": plan.construct_type,
        "fold_mode": plan.fold_mode,
        "chains": [{"role": c.role, "length": len(c.sequence)} for c in plan.chains],
        "total_length": plan.total_length,
        "warnings": plan.warnings,
        "metrics": fold_result.get("metrics"),
    }
    (rec_dir / f"{plan.record_id}.json").write_text(json.dumps(meta, indent=2))


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def plan_from_row(row: dict[str, str], config: dict) -> FoldPlan | SkipRecord:
    return build_fold_plan(
        row,
        fold_mode=config["fold_mode"],
        max_total_length=int(config["max_total_length"]),
        min_chain_length=int(config["min_chain_length"]),
        max_chain_length=config.get("max_chain_length"),
        allow_unk_x=bool(config.get("allow_unk_x", True)),
        reject_if_construct_type_mismatch=bool(config.get("reject_if_construct_type_mismatch", True)),
    )


def skip_to_dict(skip: SkipRecord) -> dict:
    return asdict(skip)
