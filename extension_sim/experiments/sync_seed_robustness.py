"""3-peer deterministic replay sync across multiple random seeds."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import EXPERIMENT_SEEDS, merge_seed_stats
from src.fb13 import load_fb13
from src.ledger import LedgerConfig
from src.network import run_stream_fb13_replicated
from src.paper_sim import PAPER_NUM_FACTS, paper_submission_stream

RESULTS = ROOT / "results"
SYNC_SUBMISSIONS = 500

METRIC_KEYS = [
    "in_sync",
    "all_states_match",
    "all_chain_lengths_match",
    "all_chains_valid",
    "sota_accuracy",
    "chain_blocks",
]


def _eval_seed(seed: int) -> dict:
    groups = load_fb13(max_groups=PAPER_NUM_FACTS, pairs_only=True)
    events = paper_submission_stream(groups, total_submissions=SYNC_SUBMISSIONS, seed=seed)
    network = run_stream_fb13_replicated(
        groups, events, LedgerConfig(), chain_batch_size=20, num_peers=3
    )
    report = network.sync_report()
    acc = network.leader.ledger.sota_accuracy()
    return {
        "seed": seed,
        "submissions": SYNC_SUBMISSIONS,
        "in_sync": 1.0 if report["in_sync"] else 0.0,
        "all_states_match": 1.0 if report["all_states_match"] else 0.0,
        "all_chain_lengths_match": 1.0 if report["all_chain_lengths_match"] else 0.0,
        "all_chains_valid": 1.0 if report["all_chains_valid"] else 0.0,
        "sota_accuracy": acc,
        "chain_blocks": float(len(network.leader.blockchain.chain)),
        "state_digests": report["state_digests"],
        "sync_report": report,
    }


def run():
    RESULTS.mkdir(exist_ok=True)
    per_seed = [_eval_seed(seed) for seed in EXPERIMENT_SEEDS]
    all_ok = all(r["in_sync"] == 1.0 for r in per_seed)

    summary = merge_seed_stats(
        {
            "num_peers": 3,
            "submissions": SYNC_SUBMISSIONS,
            "all_seeds_in_sync": all_ok,
        },
        METRIC_KEYS,
        per_seed,
    )

    out = RESULTS / "sync_seed_robustness.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved {out}")
    if not all_ok:
        raise SystemExit("Peer sync failed for one or more seeds")


if __name__ == "__main__":
    run()
