"""
FB13-style fact groups for paper-aligned simulation (Sec. VI-B).

Paper [44] FB13: pairs sharing (head, relation) with correct/incorrect tails (~23,733 pairs).
Experiments use 100 fact groups × 2 triples → 5,000 submissions.

Place file at: data/fb13_pairs.tsv
Columns (tab-separated, no header):
  head \\t relation \\t tail \\t label
  label: 1 = correct tail, 0 = incorrect tail

If missing, a small built-in sample is used (tests still run).
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

Triple = Tuple[str, str, str]

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_FB13 = DATA_DIR / "fb13_pairs.tsv"
DEFAULT_FB13_PAPER = DATA_DIR / "fb13_pairs_paper.tsv"  # test-only 1 pos + 1 neg per (h,r)


@dataclass
class FactGroup:
    fact_key: Tuple[str, str]  # (head, relation)
    ground_truth: Triple
    candidates: List[Triple]  # usually [correct, incorrect]


def _builtin_sample() -> List[FactGroup]:
    """Minimal stand-in when FB13 file is absent."""
    groups = []
    for i in range(20):
        h, r = f"/m/entity_{i}", f"/r/relation_{i % 5}"
        good = (h, r, f"/m/tail_correct_{i}")
        bad = (h, r, f"/m/tail_wrong_{i}")
        groups.append(FactGroup((h, r), good, [good, bad]))
    return groups


def load_fb13(
    path: Path | None = None,
    max_groups: int | None = None,
    pairs_only: bool = False,
) -> List[FactGroup]:
    if path is None:
        path = DEFAULT_FB13_PAPER if pairs_only else DEFAULT_FB13
    path = Path(path)
    if not path.exists() and pairs_only and DEFAULT_FB13.exists():
        path = DEFAULT_FB13
    if not path.exists():
        groups = _builtin_sample()
        if max_groups:
            return groups[:max_groups]
        return groups

    by_hr: Dict[Tuple[str, str], List[Tuple[Triple, int]]] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 4:
                continue
            h, r, t, lab = row[0].strip(), row[1].strip(), row[2].strip(), int(row[3].strip())
            key = (h, r)
            by_hr.setdefault(key, []).append(((h, r, t), lab))

    groups: List[FactGroup] = []
    rich_keys = [
        k
        for k, items in by_hr.items()
        if any(lab == 1 for _, lab in items) and any(lab == 0 for _, lab in items)
    ]
    keys = rich_keys if pairs_only else list(by_hr.keys())
    for key in keys:
        items = by_hr[key]
        correct = [tr for tr, lab in items if lab == 1]
        if not correct:
            continue
        gt = correct[0]
        wrong = [tr for tr, lab in items if lab == 0]
        if pairs_only and wrong:
            candidates = [gt, wrong[0]]
        else:
            candidates = list({tr for tr, _ in items})
        groups.append(FactGroup(key, gt, candidates))

    if max_groups:
        groups = groups[:max_groups]
    return groups


