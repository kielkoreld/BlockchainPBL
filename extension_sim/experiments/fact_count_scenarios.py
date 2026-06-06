"""Scenarios where num_confirmed_facts, total_facts, num_facts differ."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ledger import CollaborativeKGLedger, LedgerConfig
from src.metrics import evolution_metrics
from src.paper_sim import ledger_summary, run_paper_ledger

RESULTS = ROOT / "results"


def _pack(name: str, ledger: CollaborativeKGLedger) -> dict:
    base = ledger_summary(ledger)
    m = evolution_metrics(ledger)
    return {
        "scenario": name,
        "num_confirmed_facts": base["num_confirmed_facts"],
        "total_facts": base["total_facts"],
        "num_facts": m["num_facts"],  # active (not recycled) facts
        "num_confirmed_metrics_facts": m["num_confirmed_metrics_facts"],
        "num_recycled": base["num_recycled"],
        "sota_accuracy": base["sota_accuracy"],
    }


def scenario_sparse_submissions() -> dict:
    # 100 catalog facts exist, but only some become confirmed.
    ledger = run_paper_ledger(config=LedgerConfig(), total_submissions=120, seed=42)
    return _pack("sparse_submissions_on_catalog", ledger)


def scenario_mixed_recycle_pending() -> dict:
    # total > active > confirmed
    cfg = LedgerConfig(alpha=2, min_confirm=2, sota_update_margin=0.02)
    ledger = CollaborativeKGLedger(cfg)
    for cid in ("H0", "H1", "P0", "S0"):
        ledger.register_contributor(cid)

    rnd = 0
    # 4 confirmed facts
    for i in range(4):
        t = (f"ch_{i}", "rel", f"ct_{i}")
        fid = ledger.submit_triple("H0", t, rnd, ground_truth_for_new=t)
        rnd += 1
        if fid is not None:
            ledger.submit_triple("H1", t, rnd, fact_id=fid)
        rnd += 1

    # 4 pending but recent facts (not recycled yet)
    for i in range(4):
        t = (f"ph_{i}", "rel", f"pt_{i}")
        ledger.submit_triple("P0", t, rnd, ground_truth_for_new=t)
        rnd += 1

    # 4 stale spam facts -> recycled
    for i in range(4):
        t = (f"sh_{i}", "rel", f"st_{i}")
        ledger.submit_triple("S0", t, rnd, ground_truth_for_new=t)
        rnd += 1

    ledger.garbage_collect(rnd + 20)
    return _pack("mixed_confirmed_pending_recycled", ledger)


def scenario_dynamic_new_facts() -> dict:
    # New facts keep being added, only minority gets confirmed.
    cfg = LedgerConfig(alpha=10, min_confirm=2, sota_update_margin=0.02)
    ledger = CollaborativeKGLedger(cfg)
    for cid in ("A0", "A1", "B0"):
        ledger.register_contributor(cid)

    rnd = 0
    # 6 confirmed
    for i in range(6):
        t = (f"ok_h_{i}", "rel", f"ok_t_{i}")
        fid = ledger.submit_triple("A0", t, rnd, ground_truth_for_new=t)
        rnd += 1
        if fid is not None:
            ledger.submit_triple("A1", t, rnd, fact_id=fid)
        rnd += 1

    # 14 new single-submission facts (pending)
    for i in range(14):
        t = (f"new_h_{i}", "rel", f"new_t_{i}")
        ledger.submit_triple("B0", t, rnd, ground_truth_for_new=t)
        rnd += 1

    # Don't advance enough for recycle -> many active pending facts remain.
    ledger.garbage_collect(rnd + 2)
    return _pack("many_new_pending_facts", ledger)


def run():
    RESULTS.mkdir(exist_ok=True)
    rows = [
        scenario_sparse_submissions(),
        scenario_mixed_recycle_pending(),
        scenario_dynamic_new_facts(),
    ]
    out = RESULTS / "fact_count_scenarios.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    run()
