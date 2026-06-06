"""3-peer ledger sync tests (multiple seeds)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_stats import EXPERIMENT_SEEDS
from src.fb13 import load_fb13
from src.ledger import LedgerConfig
from src.network import run_stream_fb13_replicated
from src.paper_sim import PAPER_NUM_FACTS, paper_submission_stream


def _run_sync(seed: int, total_submissions: int = 120):
    groups = load_fb13(max_groups=min(20, PAPER_NUM_FACTS), pairs_only=True)
    events = paper_submission_stream(groups, total_submissions=total_submissions, seed=seed)
    network = run_stream_fb13_replicated(
        groups, events, LedgerConfig(), chain_batch_size=10, num_peers=3
    )
    return network


def test_three_peers_sync_after_replay():
    network = _run_sync(7, total_submissions=80)
    report = network.sync_report()
    assert report["in_sync"] is True, report
    assert report["all_states_match"] is True
    assert network.peers[0].ledger.sota_accuracy() == network.peers[2].ledger.sota_accuracy()


def test_three_peers_sync_all_experiment_seeds():
    for seed in EXPERIMENT_SEEDS:
        network = _run_sync(seed, total_submissions=150)
        report = network.sync_report()
        assert report["in_sync"] is True, f"seed={seed} report={report}"
        digests = [p.state_digest for p in network.peers]
        assert len(set(digests)) == 1, f"seed={seed} digests differ: {digests}"


def run_all():
    test_three_peers_sync_after_replay()
    test_three_peers_sync_all_experiment_seeds()
    print(f"All peer sync tests passed (seeds {EXPERIMENT_SEEDS}).")


if __name__ == "__main__":
    run_all()
