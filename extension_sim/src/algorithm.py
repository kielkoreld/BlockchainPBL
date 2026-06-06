"""
Multi-contributor knowledge quality evaluation — Algorithm 1 (Sec. IV).

Equations from ExportBlock notes / paper Sec. IV (Eq. 3–5):

  q_i^l = q_i^{l-1} + (1/N) * sum_{e!=i} W_{i,e}^{l-1} * Z_{i,e}^{l-1}

  W_{i,e}^{l-1} = (1/l)(1 - q_i^{l-1})           if k_e = k_i  (agree)
                = -(1/l) q_i^{l-1}               if k_e != k_i (disagree)

  Z_{i,e}^{l-1} = (1/2)(q_e^{l-1} - q_i^{l-1} + 1) q_e^{l-1}
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

Triple = Tuple[str, str, str]
TripleEntry = Tuple[Triple, float]  # (k_i, p_i)


def w_factor(l: int, q_i: float, agree: bool) -> float:
    """Eq. (4): upper bound W for one comparison at iteration l."""
    if l < 1:
        raise ValueError("iteration l must be >= 1")
    if agree:
        return (1.0 / l) * (1.0 - q_i)
    return -(1.0 / l) * q_i


def z_factor(q_i: float, q_e: float) -> float:
    """Eq. (5): update magnitude Z."""
    return 0.5 * (q_e - q_i + 1.0) * q_e


def update_quality_one_step_indices(
    q: List[float],
    triples: Sequence[Triple],
    l: int,
) -> List[float]:
    """Single iteration l over N indexed triples (Eq. 3–5)."""
    n = len(q)
    new_q = list(q)
    for i in range(n):
        qi = q[i]
        delta = 0.0
        for e in range(n):
            if e == i:
                continue
            qe = q[e]
            agree = triples[e] == triples[i]
            w = w_factor(l, qi, agree)
            z = z_factor(qi, qe)
            delta += w * z
        new_q[i] = max(0.0, min(1.0, qi + (1.0 / n) * delta))
    return new_q


def evaluate_triple_qualities(
    triples: Sequence[Triple],
    contributor_trust: Sequence[float],
    num_iterations: int = 5,
) -> Dict[Triple, float]:
    """
    Run Algorithm 1 for one F_ID group.
    Duplicate triples are merged: trust = max(p) per unique triple, then indexed run.
    """
    n = len(triples)
    if n == 0:
        return {}
    if n == 1:
        return {triples[0]: float(contributor_trust[0])}

    # Build indexed list (paper: k_1..k_N); merge same triple with max trust
    entries: List[TripleEntry] = []
    for t, p in zip(triples, contributor_trust):
        entries.append((t, float(p)))

    idx_triples = [t for t, _ in entries]
    q = [p for _, p in entries]

    for l in range(1, num_iterations + 1):
        q = update_quality_one_step_indices(q, idx_triples, l)

    out: Dict[Triple, float] = {}
    for t, qi in zip(idx_triples, q):
        out[t] = max(out.get(t, 0.0), qi)
    return out


def pick_sota(
    qualities: Dict[Triple, float],
    follower_triples: set[Triple] | None = None,
) -> Tuple[Triple, float]:
    """Highest-quality non-follower triple becomes SOTA (Sec. III-C)."""
    follower_triples = follower_triples or set()
    candidates = [(t, v) for t, v in qualities.items() if t not in follower_triples]
    if not candidates:
        candidates = list(qualities.items())
    return max(candidates, key=lambda x: x[1])


def follower_quality(sota_quality: float, lam: float) -> float:
    """Sec. III-C: Q = λ * Q_ST."""
    return lam * sota_quality
