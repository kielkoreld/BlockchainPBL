"""Multi-seed aggregation and ablation metrics (cheater defense, alpha garbage)."""

from __future__ import annotations

import statistics
from typing import Any, Callable, Dict, List, Optional, Set

from .ledger import CollaborativeKGLedger

EXPERIMENT_SEEDS = [42, 123, 456]
CHEATER_START_ROUND = 2000


def mean_std(values: List[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(statistics.mean(values)), float(statistics.stdev(values))


def merge_seed_stats(
    base_row: Dict[str, Any],
    numeric_keys: List[str],
    per_seed_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    merged = dict(base_row)
    merged["seeds"] = list(EXPERIMENT_SEEDS)
    merged["per_seed"] = per_seed_rows
    for k in numeric_keys:
        vals = [float(r[k]) for r in per_seed_rows]
        m, sd = mean_std(vals)
        merged[f"{k}_mean"] = m
        merged[f"{k}_std"] = sd
    return merged


def cheater_defense_metrics(
    ledger: CollaborativeKGLedger,
    cheater_ids: List[str],
    *,
    cheater_start_round: int = CHEATER_START_ROUND,
) -> Dict[str, float]:
    cheater_set = set(cheater_ids)
    honest_ids = [
        c
        for c in ledger.contributor_trust
        if c.startswith("C") and c not in cheater_set
    ]
    cheater_trusts = [ledger.contributor_trust[c] for c in cheater_ids if c in ledger.contributor_trust]
    honest_trusts = [ledger.contributor_trust[c] for c in honest_ids]

    cheater_subs_after = 0
    cheater_follower_after = 0
    cheater_subs_total = 0
    cheater_follower_total = 0
    honest_follower_after = 0
    honest_subs_after = 0

    for fact in ledger.facts.values():
        if fact.recycled:
            continue
        for sub in fact.submissions:
            is_cheater = sub.contributor_id in cheater_set
            if is_cheater:
                cheater_subs_total += 1
                if sub.is_follower:
                    cheater_follower_total += 1
            elif sub.contributor_id in honest_ids:
                if sub.round_idx >= cheater_start_round:
                    honest_subs_after += 1
                    if sub.is_follower:
                        honest_follower_after += 1

            if sub.round_idx >= cheater_start_round and is_cheater:
                cheater_subs_after += 1
                if sub.is_follower:
                    cheater_follower_after += 1

    confirmed = [
        f
        for f in ledger.facts.values()
        if f.confirmed and not f.recycled and f.sota_triple is not None
    ]
    wrong_sota = [f for f in confirmed if f.sota_triple != f.ground_truth]
    wrong_with_cheater = sum(
        1
        for f in wrong_sota
        if any(s.contributor_id in cheater_set for s in f.submissions)
    )

    avg_cheater = sum(cheater_trusts) / len(cheater_trusts) if cheater_trusts else 0.0
    avg_honest = sum(honest_trusts) / len(honest_trusts) if honest_trusts else 0.0

    return {
        "avg_cheater_trust": avg_cheater,
        "avg_honest_trust": avg_honest,
        "cheater_trust_gap": avg_honest - avg_cheater,
        "cheater_follower_rate": cheater_follower_total / max(cheater_subs_total, 1),
        "cheater_follower_rate_after_start": cheater_follower_after / max(cheater_subs_after, 1),
        "honest_follower_rate_after_start": honest_follower_after / max(honest_subs_after, 1),
        "follower_submissions": float(
            sum(
                1
                for f in ledger.facts.values()
                for s in f.submissions
                if s.is_follower
            )
        ),
        "wrong_sota_facts": float(len(wrong_sota)),
        "wrong_sota_rate": len(wrong_sota) / max(len(confirmed), 1),
        "wrong_sota_with_cheater_involved": float(wrong_with_cheater),
        "cheater_submissions_after_start": float(cheater_subs_after),
    }


def alpha_garbage_metrics(
    ledger: CollaborativeKGLedger,
    spam_fids: Set[int],
    legit_new_fids: Set[int],
) -> Dict[str, float]:
    spam_total = len(spam_fids)
    legit_total = len(legit_new_fids)
    spam_recycled = sum(
        1 for fid in spam_fids if ledger.facts.get(fid) is not None and ledger.facts[fid].recycled
    )
    legit_recycled = sum(
        1
        for fid in legit_new_fids
        if ledger.facts.get(fid) is not None and ledger.facts[fid].recycled
    )
    legit_confirmed = sum(
        1
        for fid in legit_new_fids
        if ledger.facts.get(fid) is not None and ledger.facts[fid].confirmed and not ledger.facts[fid].recycled
    )
    catalog_recycled = sum(
        1
        for f in ledger.facts.values()
        if f.catalog_fact and f.recycled
    )
    return {
        "spam_total": float(spam_total),
        "spam_recycled": float(spam_recycled),
        "spam_recall": spam_recycled / max(spam_total, 1),
        "legit_new_total": float(legit_total),
        "legit_confirmed": float(legit_confirmed),
        "legit_false_recycle": float(legit_recycled),
        "legit_false_recycle_rate": legit_recycled / max(legit_total, 1),
        "catalog_false_recycle": float(catalog_recycled),
        "catalog_false_recycle_rate": catalog_recycled / max(
            sum(1 for f in ledger.facts.values() if f.catalog_fact), 1
        ),
        "num_recycled_total": float(len(ledger.recycled_fact_ids)),
    }


def run_multi_seed(
    run_one: Callable[[int], Dict[str, Any]],
    seeds: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Run experiment per seed; return list of per-seed dicts."""
    seeds = seeds or EXPERIMENT_SEEDS
    return [run_one(s) for s in seeds]
