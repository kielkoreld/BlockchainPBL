"""FB13 paper-mode smoke test (5000 submissions, 3 seeds)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import EXPERIMENT_SEEDS, merge_seed_stats
from src.metrics import evolution_metrics
from src.paper_sim import PAPER_NUM_CONTRIBUTORS, PAPER_TOTAL_SUBMISSIONS, ledger_summary, run_paper_ledger

RESULTS = ROOT / "results"

METRIC_KEYS = [
    "num_confirmed_facts",
    "num_recycled",
    "sota_accuracy",
    "total_facts",
    "avg_sota_changes_per_fact",
    "avg_rounds_to_first_correct_sota",
    "churn_rate",
    "stable_fact_ratio",
    "num_facts",
    "num_confirmed_metrics_facts",
]


def _eval_seed(seed: int) -> dict:
    ledger = run_paper_ledger(seed=seed)
    metrics = evolution_metrics(ledger)
    return {
        "seed": seed,
        **ledger_summary(ledger),
        **metrics,
    }


def run():
    RESULTS.mkdir(exist_ok=True)
    per_seed = [_eval_seed(seed) for seed in EXPERIMENT_SEEDS]
    out = merge_seed_stats(
        {
            "paper_mode": True,
            "num_contributors": PAPER_NUM_CONTRIBUTORS,
            "total_submissions": PAPER_TOTAL_SUBMISSIONS,
        },
        METRIC_KEYS,
        per_seed,
    )
    path = RESULTS / "fb13_smoke.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"Saved {path} (seeds={EXPERIMENT_SEEDS})")


if __name__ == "__main__":
    run()
