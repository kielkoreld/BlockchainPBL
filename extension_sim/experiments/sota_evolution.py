"""SOTA evolution metrics on FB13 paper simulation (3 seeds)."""

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
from src.paper_sim import run_paper_ledger

RESULTS = ROOT / "results"

METRIC_KEYS = [
    "sota_accuracy",
    "avg_sota_changes_per_fact",
    "avg_rounds_to_first_correct_sota",
    "churn_rate",
    "stable_fact_ratio",
    "num_facts",
    "num_confirmed_metrics_facts",
    "num_recycled",
    "timeline_len",
]


def _eval_seed(seed: int) -> dict:
    ledger = run_paper_ledger(config=LedgerConfig(), seed=seed)
    metrics = evolution_metrics(ledger)
    timeline_len = sum(len(f.sota_history) for f in ledger.facts.values())
    return {"seed": seed, "timeline_len": float(timeline_len), **metrics}


def run():
    os.environ.setdefault("MPLBACKEND", "Agg")
    RESULTS.mkdir(exist_ok=True)
    per_seed = [_eval_seed(seed) for seed in EXPERIMENT_SEEDS]
    payload = merge_seed_stats({}, METRIC_KEYS, per_seed)

    out = RESULTS / "sota_evolution.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _maybe_plot(per_seed, payload)
    print(json.dumps(payload, indent=2))
    print(f"Saved {out} (seeds={EXPERIMENT_SEEDS})")


def _maybe_plot(per_seed: list[dict], summary: dict):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    names = ["accuracy", "churn", "stable_ratio"]
    means = [
        summary["sota_accuracy_mean"],
        summary["churn_rate_mean"],
        summary["stable_fact_ratio_mean"],
    ]
    stds = [
        summary["sota_accuracy_std"],
        summary["churn_rate_std"],
        summary["stable_fact_ratio_std"],
    ]
    x = range(len(names))
    ax2.bar(x, means, yerr=stds, capsize=4, color=["#1565c0", "#c62828", "#2e7d32"])
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(names)
    ax2.set_ylim(0, 1.05)
    ax2.set_title(f"SOTA evolution summary (n={len(EXPERIMENT_SEEDS)} seeds)")
    plt.tight_layout()
    plt.savefig(RESULTS / "sota_evolution_summary.png", dpi=150)
    plt.close()

    fig, ax = plt.subplots(figsize=(7, 4))
    seeds = [r["seed"] for r in per_seed]
    acc = [r["sota_accuracy"] for r in per_seed]
    tl = [r["timeline_len"] for r in per_seed]
    ax.bar([str(s) for s in seeds], acc, label="sota_accuracy", color="#1565c0")
    ax.set_ylabel("sota_accuracy")
    ax.set_xlabel("seed")
    ax2b = ax.twinx()
    ax2b.plot([str(s) for s in seeds], tl, "o--", color="orange", label="timeline_len")
    ax2b.set_ylabel("SOTA change events")
    lines1, lab1 = ax.get_legend_handles_labels()
    lines2, lab2 = ax2b.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lab1 + lab2, loc="upper right", fontsize=8)
    ax.set_title("Per-seed accuracy vs SOTA change count")
    plt.tight_layout()
    plt.savefig(RESULTS / "sota_evolution_per_seed.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run()
