# ESMFold2 pipeline for `abag_foldable_constructs_v3.csv`

Self-contained install under `esmfold2/` (venv + Hugging Face cache + outputs). Pull the repo on Vista, run setup once, then fold from the CSV.

## Quick start (Vista)

```bash
cd /scratch/11104/pbhat125/ab-ag-data   # your clone path

bash esmfold2/setup.sh
source esmfold2/env.sh

# Optional: download ~13GB weights before batch jobs
PREFETCH_WEIGHTS=1 bash esmfold2/setup.sh

# Classify rows (no GPU)
python esmfold2/bin/manifest_csv.py

# Smoke test on GPU login node or idev
bash esmfold2/run_local.sh

# Batch via Slurm (edit partition/time as needed)
mkdir -p esmfold2/logs
FOLD_LIMIT=100 sbatch esmfold2/slurm/vista_fold.slurm
```

## Configuration

- Defaults: `config.defaults.yaml` (tracked in git)
- Machine-specific: `config.local.yaml` (created by `setup.sh`, gitignored)

Important keys:

| Key | Meaning |
|-----|---------|
| `fold_mode` | `complex` (Ab + Ag multimer), `antibody`, or `antigen` |
| `max_total_length` | Skip rows when sum of chain lengths exceeds this (GPU memory) |
| `allow_unk_x` | Allow `X` in sequences (mapped to UNK by ESMFold2) |
| `num_diffusion_samples` | Lower (4–8) on 24GB GPUs; see Biohub guidance |

For **24GB** nodes, start with `max_total_length: 500` and `num_diffusion_samples: 8`.  
For **H100 80GB**, `max_total_length: 2000` matches Biohub’s rough upper bound.

## Guardrails (CSV → fold plan)

Each row is validated before folding:

- **`construct_type`** must match sequences: `FV` (H+L), `SD-H` (H only), `SD-L` (L only). Mismatches are **skipped** unless you disable `reject_if_construct_type_mismatch`.
- **`complex` mode** requires `antigen_seq` and at least one of `heavy_seq` / `light_seq`.
- Empty **`scfv_seq`** is ignored (column unused in v3).
- Per-chain min length, optional max chain length, and **total length** budget.
- Invalid characters → skip.

Multimer chain order: **heavy → light → antigen** (partial Ab chains are OK for `SD-*`).

## Outputs

```
esmfold2/outputs/<run>/<record_id>/
  ABAG-000001.pdb
  ABAG-000001.json    # chain lengths, pTM / ipTM when multimer
```

Skip/fold log: `fold_log.jsonl` in the output directory.

## Environment layout (gitignored)

```
esmfold2/.venv/
esmfold2/cache/huggingface/   # model weights
esmfold2/cache/torch/
esmfold2/outputs/
esmfold2/manifests/
esmfold2/config.local.yaml
```

## CLI reference

```bash
python esmfold2/bin/manifest_csv.py --help
python esmfold2/bin/fold_csv.py --help

# Single record
python esmfold2/bin/fold_csv.py --record-id ABAG-000001

# Dry-run planning without loading the model
python esmfold2/bin/fold_csv.py --dry-run --limit 100
```

## Notes

- ESMFold2 predicts **structures from sequence**; low **ipTM** on Ab–Ag multimers is common.
- This pipeline does **not** replace dedicated Ab–Ag docking tools; it standardizes folding from your CSV with length and construct checks.
- If `setup.sh` picks the wrong CUDA wheel, set `TORCH_CUDA_INDEX` or `INSTALL_CUDA_TORCH=0` and install PyTorch manually, then re-run setup.
