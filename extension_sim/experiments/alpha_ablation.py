"""α ablation on full FB13 paper sim (5000) + injected spam/legit F_IDs, 3 seeds."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import EXPERIMENT_SEEDS, alpha_garbage_metrics, merge_seed_stats
from src.ledger import LedgerConfig
from src.paper_sim import PAPER_TOTAL_SUBMISSIONS, ledger_summary, run_paper_alpha_ledger

RESULTS = ROOT / "results"
ALPHA_VALUES = [2, 5, 10, 15, 20, 30]

METRIC_KEYS = [
    "sota_accuracy",
    "num_confirmed_facts",
    "spam_recall",
    "spam_recycled",
    "legit_false_recycle_rate",
    "legit_false_recycle",
    "legit_confirmed",
    "catalog_false_recycle_rate",
    "num_recycled_total",
]


def _eval_alpha(alpha: float, seed: int) -> dict:
    ledger, tracking = run_paper_alpha_ledger(
        config=LedgerConfig(alpha=alpha),
        seed=seed,
    )
    summary = ledger_summary(ledger)
    garbage = alpha_garbage_metrics(
        ledger, tracking["spam_fids"], tracking["legit_new_fids"]
    )
    return {
        "alpha": alpha,
        "seed": seed,
        "paper_total_submissions": PAPER_TOTAL_SUBMISSIONS,
        "full_sim": True,
        **summary,
        **garbage,
    }


def run():
    os.environ.setdefault("MPLBACKEND", "Agg")
    RESULTS.mkdir(exist_ok=True)
    rows = []

    for alpha in ALPHA_VALUES:
        per_seed = [_eval_alpha(alpha, seed) for seed in EXPERIMENT_SEEDS]
        rows.append(merge_seed_stats({"alpha": alpha}, METRIC_KEYS, per_seed))

    out = RESULTS / "alpha_ablation.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _maybe_plot(rows)
    print(f"Saved {out} (FB13 {PAPER_TOTAL_SUBMISSIONS} + spam/legit F_ID, seeds={EXPERIMENT_SEEDS})")


def _maybe_plot(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    xs = [r["alpha"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.errorbar(
        xs,
        [r["spam_recall_mean"] for r in rows],
        yerr=[r["spam_recall_std"] for r in rows],
        fmt="o-",
        capsize=3,
        label="spam recall",
    )
    ax.errorbar(
        xs,
        [r["legit_false_recycle_rate_mean"] for r in rows],
        yerr=[r["legit_false_recycle_rate_std"] for r in rows],
        fmt="s--",
        capsize=3,
        label="legit false recycle",
    )
    ax.errorbar(
        xs,
        [r["catalog_false_recycle_rate_mean"] for r in rows],
        yerr=[r["catalog_false_recycle_rate_std"] for r in rows],
        fmt="^:",
        capsize=3,
        label="catalog false recycle",
    )
    ax.set_xlabel("alpha")
    ax.set_ylim(-0.05, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_title(f"alpha ablation (full FB13 sim, n={len(EXPERIMENT_SEEDS)} seeds)")
    plt.tight_layout()
    plt.savefig(RESULTS / "alpha_ablation.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run()
