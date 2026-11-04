from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from abag_fold.constants import CHAIN_ANTIGEN, CHAIN_HEAVY, CHAIN_LIGHT, STANDARD_AA, UNK_AA

FoldMode = Literal["complex", "antibody", "antigen"]
ConstructType = Literal["FV", "SD-H", "SD-L"]


@dataclass
class ChainSpec:
    role: str
    sequence: str


@dataclass
class FoldPlan:
    record_id: str
    construct_type: str
    fold_mode: FoldMode
    chains: list[ChainSpec]
    total_length: int
    chain_lengths: dict[str, int]
    warnings: list[str] = field(default_factory=list)


@dataclass
class SkipRecord:
    record_id: str
    reason: str
    detail: str = ""


def _normalize_seq(raw: str) -> str:
    return raw.strip().upper().replace(" ", "")


def _validate_sequence(seq: str, allow_unk_x: bool) -> tuple[bool, str]:
    if not seq:
        return False, "empty sequence"
    bad = {c for c in seq if c not in STANDARD_AA and c not in UNK_AA}
    if bad:
        return False, f"non-amino-acid characters: {''.join(sorted(bad))}"
    if not allow_unk_x and any(c in seq for c in UNK_AA):
        return False, "contains ambiguous residue (X/U/O/…)"
    if len(seq) < 1:
        return False, "empty after normalization"
    return True, ""


def _construct_type_mismatch(construct_type: str, has_h: bool, has_l: bool) -> str | None:
    if construct_type == "FV":
        if not has_h or not has_l:
            return "construct_type FV but missing heavy and/or light sequence"
    elif construct_type == "SD-H":
        if not has_h or has_l:
            return "construct_type SD-H but heavy missing or light present"
    elif construct_type == "SD-L":
        if not has_l or has_h:
            return "construct_type SD-L but light missing or heavy present"
    return None


def build_fold_plan(
    row: dict[str, str],
    *,
    fold_mode: FoldMode,
    max_total_length: int,
    min_chain_length: int,
    max_chain_length: int | None,
    allow_unk_x: bool,
    reject_if_construct_type_mismatch: bool,
) -> FoldPlan | SkipRecord:
    record_id = (row.get("record_id") or "").strip()
    if not record_id:
        return SkipRecord("", "missing record_id")

    construct_type = (row.get("construct_type") or "").strip()
    heavy = _normalize_seq(row.get("heavy_seq") or "")
    light = _normalize_seq(row.get("light_seq") or "")
    antigen = _normalize_seq(row.get("antigen_seq") or "")

    has_h, has_l = bool(heavy), bool(light)
    warnings: list[str] = []

    mismatch = _construct_type_mismatch(construct_type, has_h, has_l)
    if mismatch:
        if reject_if_construct_type_mismatch:
            return SkipRecord(record_id, "construct_type_mismatch", mismatch)
        warnings.append(mismatch)

    chains: list[ChainSpec] = []
    if fold_mode in ("complex", "antibody"):
        if has_h:
            chains.append(ChainSpec(CHAIN_HEAVY, heavy))
        if has_l:
            chains.append(ChainSpec(CHAIN_LIGHT, light))
    if fold_mode in ("complex", "antigen"):
        if antigen:
            chains.append(ChainSpec(CHAIN_ANTIGEN, antigen))

    if fold_mode == "complex":
        if not antigen:
            return SkipRecord(record_id, "missing_antigen", "complex mode requires antigen_seq")
        if not has_h and not has_l:
            return SkipRecord(record_id, "missing_antibody", "complex mode requires heavy and/or light")
    elif fold_mode == "antibody":
        if not has_h and not has_l:
            return SkipRecord(record_id, "missing_antibody", "antibody mode requires heavy and/or light")
    elif fold_mode == "antigen":
        if not antigen:
            return SkipRecord(record_id, "missing_antigen", "antigen mode requires antigen_seq")

    for ch in chains:
        ok, msg = _validate_sequence(ch.sequence, allow_unk_x)
        if not ok:
            return SkipRecord(record_id, "invalid_sequence", f"{ch.role}: {msg}")
        if len(ch.sequence) < min_chain_length:
            return SkipRecord(
                record_id,
                "chain_too_short",
                f"{ch.role} length {len(ch.sequence)} < min {min_chain_length}",
            )
        if max_chain_length is not None and len(ch.sequence) > max_chain_length:
            return SkipRecord(
                record_id,
                "chain_too_long",
                f"{ch.role} length {len(ch.sequence)} > max {max_chain_length}",
            )

    total = sum(len(c.sequence) for c in chains)
    if total > max_total_length:
        return SkipRecord(
            record_id,
            "exceeds_max_total_length",
            f"total {total} > max_total_length {max_total_length}",
        )

    chain_lengths = {c.role: len(c.sequence) for c in chains}
    return FoldPlan(
        record_id=record_id,
        construct_type=construct_type,
        fold_mode=fold_mode,
        chains=chains,
        total_length=total,
        chain_lengths=chain_lengths,
        warnings=warnings,
    )


def pick_diffusion_samples(total_length: int, rules: list[dict], default: int) -> int:
    for rule in sorted(rules, key=lambda r: r["max_total"]):
        if total_length <= rule["max_total"]:
            return int(rule["samples"])
    return default
