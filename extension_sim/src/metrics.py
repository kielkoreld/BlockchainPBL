"""SOTA evolution metrics (extension experiment 3)."""

from __future__ import annotations

from typing import Dict, List

from .ledger import CollaborativeKGLedger
from .types import FactState


def evolution_metrics(ledger: CollaborativeKGLedger) -> Dict[str, float]:
    confirmed_facts: List[FactState] = [
        f for f in ledger.facts.values() if f.confirmed and not f.recycled
    ]
    active_facts: List[FactState] = [f for f in ledger.facts.values() if not f.recycled]
    if not confirmed_facts:
        return {
            "sota_accuracy": 0.0,
            "avg_sota_changes_per_fact": 0.0,
            "avg_rounds_to_first_correct_sota": 0.0,
            "churn_rate": 0.0,
            "stable_fact_ratio": 0.0,
            "num_facts": float(len(active_facts)),
            "num_confirmed_metrics_facts": 0.0,
            "num_recycled": float(len(ledger.recycled_fact_ids)),
        }

    total_changes = sum(len(f.sota_history) for f in confirmed_facts)
    rounds_to_correct = []
    stable = 0

    for f in confirmed_facts:
        if not f.sota_history:
            if f.sota_triple == f.ground_truth:
                rounds_to_correct.append(0)
                stable += 1
            continue
        for i, ch in enumerate(f.sota_history):
            if ch.new_triple == f.ground_truth:
                rounds_to_correct.append(ch.round_idx - f.created_round)
                break
        if f.sota_triple == f.ground_truth and len(f.sota_history) <= 1:
            stable += 1

    total_submissions = sum(len(f.submissions) for f in confirmed_facts)
    churn = total_changes / max(total_submissions, 1)

    return {
        "sota_accuracy": ledger.sota_accuracy(),
        "avg_sota_changes_per_fact": total_changes / len(confirmed_facts),
        "avg_rounds_to_first_correct_sota": (
            sum(rounds_to_correct) / len(rounds_to_correct) if rounds_to_correct else float("nan")
        ),
        "churn_rate": churn,
        "stable_fact_ratio": stable / len(confirmed_facts),
        "num_facts": len(active_facts),
        "num_confirmed_metrics_facts": len(confirmed_facts),
        "num_recycled": len(ledger.recycled_fact_ids),
    }
