"""Multimer featurization for ESMFold2 (Hugging Face notebook pattern)."""

from __future__ import annotations

def prepare_multimer_features(chains: list[str], device=None) -> dict:
    import torch
    from transformers.models.esmfold2.protein_utils import prepare_protein_features

    if not chains:
        raise ValueError("At least one chain is required")
    if any(not c for c in chains):
        raise ValueError("All chains must be non-empty")

    features = prepare_protein_features("".join(chains), device=device)
    unique_chains = list(dict.fromkeys(chains))
    asym_id, entity_id, sym_id, residue_index = [], [], [], []
    for chain_idx, chain in enumerate(chains):
        asym_id.extend([chain_idx] * len(chain))
        entity_id.extend([unique_chains.index(chain)] * len(chain))
        sym_id.extend([chains[:chain_idx].count(chain)] * len(chain))
        residue_index.extend(range(len(chain)))
    for key, values in (
        ("asym_id", asym_id),
        ("entity_id", entity_id),
        ("sym_id", sym_id),
        ("residue_index", residue_index),
    ):
        features[key] = torch.tensor(values, dtype=features[key].dtype).unsqueeze(0).to(
            features[key].device
        )
    return features
