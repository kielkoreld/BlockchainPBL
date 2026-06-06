"""SOTA update margin ablation: accuracy-stability trade-off (3 seeds)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import EXPERIMENT_SEEDS, merge_seed_stats
from src.ledger import LedgerConfig
from src.metrics import evolution_metrics
from src.paper_sim import ledger_summary, run_paper_ledger

RESULTS = ROOT / "results"
MARGINS = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]

METRIC_KEYS = [
    "sota_accuracy",
    "avg_sota_changes_per_fact",
    "churn_rate",
    "stable_fact_ratio",
    "avg_rounds_to_first_correct_sota",
    "num_confirmed_facts",
    "total_facts",
    "num_facts",
]


def _eval_margin(m: float, seed: int) -> dict:
    ledger = run_paper_ledger(config=LedgerConfig(sota_update_margin=m), seed=seed)
    summary = ledger_summary(ledger)
    metrics = evolution_metrics(ledger)
    return {
        "sota_update_margin": m,
        "seed": seed,
        **summary,
        **metrics,
    }


def run():
    os.environ.setdefault("MPLBACKEND", "Agg")
    RESULTS.mkdir(exist_ok=True)
    rows = []

    for m in MARGINS:
        per_seed = [_eval_margin(m, seed) for seed in EXPERIMENT_SEEDS]
        rows.append(merge_seed_stats({"sota_update_margin": m}, METRIC_KEYS, per_seed))

    out_json = RESULTS / "sota_margin_ablation.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _maybe_plot(rows)
    print(f"Saved {out_json} (seeds={EXPERIMENT_SEEDS})")


def _maybe_plot(rows: list[dict]):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    xs = [r["sota_update_margin"] for r in rows]
    acc_m = [r["sota_accuracy_mean"] for r in rows]
    acc_s = [r["sota_accuracy_std"] for r in rows]
    stab_m = [r["stable_fact_ratio_mean"] for r in rows]
    stab_s = [r["stable_fact_ratio_std"] for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.errorbar(xs, acc_m, yerr=acc_s, fmt="o-", capsize=3, label="accuracy")
    ax1.set_xlabel("sota_update_margin")
    ax1.set_ylabel("accuracy")
    ax1.set_ylim(0, 1.0)
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.errorbar(
        xs, stab_m, yerr=stab_s, fmt="s--", color="seagreen", capsize=3, label="stable_ratio"
    )
    ax2.set_ylabel("stable_fact_ratio")
    ax2.set_ylim(0, 1.0)
    lines1, labs1 = ax1.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labs1 + labs2, loc="best")
    plt.title(f"Accuracy-Stability vs margin (n={len(EXPERIMENT_SEEDS)} seeds)")
    plt.tight_layout()
    plt.savefig(RESULTS / "sota_margin_curve.png", dpi=150)
    plt.close()

    fig2, ax = plt.subplots(figsize=(6, 5))
    for r in rows:
        ax.errorbar(
            r["stable_fact_ratio_mean"],
            r["sota_accuracy_mean"],
            xerr=r["stable_fact_ratio_std"],
            yerr=r["sota_accuracy_std"],
            fmt="o",
            capsize=3,
            label=f"m={r['sota_update_margin']}",
        )
    ax.set_xlabel("stable_fact_ratio")
    ax.set_ylabel("sota_accuracy")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, loc="lower left")
    plt.title("Accuracy-Stability Pareto view (mean ± std)")
    plt.tight_layout()
    plt.savefig(RESULTS / "sota_margin_pareto.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run()
