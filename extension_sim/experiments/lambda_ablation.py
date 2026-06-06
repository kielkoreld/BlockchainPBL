"""λ ablation on full FB13 paper simulation (5000) + Cheater (SOTA copy), 3 seeds."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import (
    EXPERIMENT_SEEDS,
    cheater_defense_metrics,
    merge_seed_stats,
)
from src.ledger import LedgerConfig
from src.paper_sim import ledger_summary, run_paper_ledger

RESULTS = ROOT / "results"
LAMBDA_VALUES = [0.2, 0.35, 0.5, 0.65, 0.8, 1.0]
CHEATER_IDS = ["C0", "C1", "C2"]

METRIC_KEYS = [
    "sota_accuracy",
    "num_confirmed_facts",
    "avg_cheater_trust",
    "avg_honest_trust",
    "cheater_trust_gap",
    "cheater_follower_rate",
    "cheater_follower_rate_after_start",
    "honest_follower_rate_after_start",
    "follower_submissions",
    "wrong_sota_facts",
    "wrong_sota_rate",
    "wrong_sota_with_cheater_involved",
    "cheater_submissions_after_start",
]


def _eval_lambda(lam: float, seed: int) -> dict:
    ledger = run_paper_ledger(
        config=LedgerConfig(lam=lam),
        seed=seed,
        cheater_ids=CHEATER_IDS,
    )
    summary = ledger_summary(ledger)
    defense = cheater_defense_metrics(ledger, CHEATER_IDS)
    return {"lambda": lam, "seed": seed, **summary, **defense}


def run():
    os.environ.setdefault("MPLBACKEND", "Agg")
    RESULTS.mkdir(exist_ok=True)
    rows = []

    for lam in LAMBDA_VALUES:
        per_seed = [_eval_lambda(lam, seed) for seed in EXPERIMENT_SEEDS]
        rows.append(
            merge_seed_stats({"lambda": lam}, METRIC_KEYS, per_seed)
        )

    out_json = RESULTS / "lambda_ablation.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _maybe_plot(rows)
    print(f"Saved {out_json} ({len(EXPERIMENT_SEEDS)} seeds: {EXPERIMENT_SEEDS})")


def _maybe_plot(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    xs = [r["lambda"] for r in rows]
    acc_m = [r["sota_accuracy_mean"] for r in rows]
    acc_s = [r["sota_accuracy_std"] for r in rows]
    cheat_m = [r["avg_cheater_trust_mean"] for r in rows]
    cheat_s = [r["avg_cheater_trust_std"] for r in rows]
    gap_m = [r["cheater_trust_gap_mean"] for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.errorbar(xs, acc_m, yerr=acc_s, fmt="o-", capsize=3, label="SOTA accuracy")
    ax1.set_xlabel("lambda")
    ax1.set_ylabel("SOTA accuracy")
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.errorbar(
        xs, cheat_m, yerr=cheat_s, fmt="s--", color="crimson", capsize=3, label="avg cheater trust"
    )
    ax2.plot(xs, gap_m, ":", color="green", label="honest-cheater trust gap")
    ax2.set_ylabel("trust / gap")
    lines1, lab1 = ax1.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lab1 + lab2, loc="best", fontsize=8)
    plt.title(f"lambda ablation (FB13 5000, Cheater, n={len(EXPERIMENT_SEEDS)} seeds)")
    plt.tight_layout()
    plt.savefig(RESULTS / "lambda_ablation.png", dpi=150)
    plt.close()

    fig2, ax = plt.subplots(figsize=(8, 4))
    wrong_m = [r["wrong_sota_rate_mean"] for r in rows]
    wrong_s = [r["wrong_sota_rate_std"] for r in rows]
    ax.errorbar(xs, wrong_m, yerr=wrong_s, fmt="o-", color="purple", capsize=3)
    ax.set_xlabel("lambda")
    ax.set_ylabel("wrong SOTA rate")
    ax.set_title("Wrong SOTA rate vs lambda")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(RESULTS / "lambda_ablation_wrong_sota.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run()
