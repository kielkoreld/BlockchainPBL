"""
Verify Eq. (3)-(5) implementation against hand-calculated values.
Run: python tests/test_algorithm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.algorithm import (
    evaluate_triple_qualities,
    update_quality_one_step_indices,
    w_factor,
    z_factor,
)


def test_w_agree_disagree():
    assert abs(w_factor(1, 0.7, agree=True) - 0.3) < 1e-9
    assert abs(w_factor(1, 0.7, agree=False) + 0.7) < 1e-9
    assert abs(w_factor(2, 0.7, agree=True) - 0.15) < 1e-9


def test_z_factor():
    # Z = 0.5 * (0.8 - 0.7 + 1) * 0.8 = 0.44
    assert abs(z_factor(0.7, 0.8) - 0.44) < 1e-9


def test_one_iteration_n2_disagree():
    """N=2, disagreeing triples, l=1 — matches ExportBlock manual derivation."""
    t1 = ("a", "r", "b")
    t2 = ("a", "r", "c")
    q1 = update_quality_one_step_indices([0.7, 0.8], [t1, t2], l=1)
    assert abs(q1[0] - 0.546) < 1e-3
    assert abs(q1[1] - 0.674) < 1e-3


def test_agree_increases_quality():
    """Two submissions of the same triple (e!=i, k_e=k_i) -> positive W."""
    t = ("h", "r", "tail")
    q1 = update_quality_one_step_indices([0.4, 0.6], [t, t], l=1)
    assert q1[0] > 0.4
    assert q1[1] > 0.6


def test_sota_picks_higher_after_iterations():
    correct = ("e1", "rel", "tail_ok")
    wrong = ("e1", "rel", "tail_bad")
    # More trusted contributor submits correct; others noisy
    qualities = evaluate_triple_qualities(
        [correct, wrong, wrong],
        [0.9, 0.4, 0.35],
        num_iterations=10,
    )
    assert qualities[correct] >= qualities[wrong]


def run_all():
    test_w_agree_disagree()
    test_z_factor()
    test_one_iteration_n2_disagree()
    test_agree_increases_quality()
    test_sota_picks_higher_after_iterations()
    print("All algorithm tests passed.")


if __name__ == "__main__":
    run_all()
