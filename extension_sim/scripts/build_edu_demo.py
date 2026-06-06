#!/usr/bin/env python3
"""
Run 3-peer replicated sim + export HTML dashboard.

Usage (WSL):
  cd extension_sim
  python3 scripts/build_edu_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ledger import LedgerConfig
from src.metrics import evolution_metrics
from src.network import run_stream_fb13_replicated
from src.paper_sim import (
    PAPER_NUM_FACTS,
    ledger_summary,
    paper_submission_stream,
)
from src.fb13 import load_fb13
from viz.dashboard import render_dashboard

RESULTS = ROOT / "results"
DEMO_SUBMISSIONS = 1500
NUM_PEERS = 3


def main():
    RESULTS.mkdir(exist_ok=True)
    print(f"Running {NUM_PEERS}-peer replicated sim ({DEMO_SUBMISSIONS} submissions)...")
    groups = load_fb13(max_groups=PAPER_NUM_FACTS, pairs_only=True)
    events = paper_submission_stream(groups, total_submissions=DEMO_SUBMISSIONS, seed=42)
    network = run_stream_fb13_replicated(
        groups, events, LedgerConfig(), chain_batch_size=20, num_peers=NUM_PEERS
    )
    ledger = network.leader.ledger
    chain = ledger.blockchain
    sync_report = network.sync_report()
    assert chain is not None

    summary = {**ledger_summary(ledger), **evolution_metrics(ledger)}
    summary["demo_submissions"] = DEMO_SUBMISSIONS
    summary["num_peers"] = NUM_PEERS
    summary["chain_blocks"] = len(chain.chain)
    summary["chain_valid"] = chain.verify_chain()
    summary.update({f"sync_{k}": v for k, v in sync_report.items()})

    json_path = RESULTS / "edu_demo_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    html_path = render_dashboard(
        ledger,
        chain,
        RESULTS / "edu_dashboard.html",
        title=f"DKG 3-Peer 데모 ({DEMO_SUBMISSIONS} 제출)",
        sync_report=sync_report,
    )

    print(json.dumps(sync_report, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"Saved {json_path}")
    print(f"Saved {html_path}")


if __name__ == "__main__":
    main()
