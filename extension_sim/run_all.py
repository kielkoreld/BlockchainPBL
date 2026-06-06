#!/usr/bin/env python3
"""Run all extension experiments (λ, α, SOTA evolution, margin curve, fact-count scenarios)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from experiments.alpha_ablation import run as run_alpha
from experiments.fact_count_scenarios import run as run_fact_count
from experiments.fb13_smoke import run as run_fb13_smoke
from experiments.lambda_ablation import run as run_lambda
from experiments.sota_evolution import run as run_evolution
from experiments.sota_margin_ablation import run as run_margin
from experiments.sync_seed_robustness import run as run_sync_seeds
from tests.test_algorithm import run_all as run_algo_tests
from tests.test_chain import run_all as run_chain_tests
from tests.test_peer_sync import run_all as run_peer_sync_tests


def main():
    print("=== Algorithm unit tests (Eq. 3-5) ===")
    run_algo_tests()
    print("=== Chain unit tests ===")
    run_chain_tests()
    print("=== Peer sync tests (3 nodes, multi-seed) ===")
    run_peer_sync_tests()
    print("=== 3-peer sync robustness (seeds 42, 123, 456) ===")
    run_sync_seeds()
    print("=== FB13 smoke ===")
    run_fb13_smoke()
    print("=== λ ablation ===")
    run_lambda()
    print("=== α ablation ===")
    run_alpha()
    print("=== SOTA evolution ===")
    run_evolution()
    print("=== SOTA margin ablation (accuracy-stability curve) ===")
    run_margin()
    print("=== Fact count scenarios ===")
    run_fact_count()
    print("Done. See extension_sim/results/")


if __name__ == "__main__":
    main()
