"""
Paper-aligned simulation (Wang et al. VI-B): FB13, 100 facts, ~5000 submissions.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Set

from .fb13 import FactGroup, load_fb13
from .ledger import CollaborativeKGLedger, LedgerConfig
from .runner import run_stream_fb13

# Paper VI-B (ExportBlock notes)
PAPER_NUM_FACTS = 100
PAPER_NUM_CONTRIBUTORS = 25
PAPER_TOTAL_SUBMISSIONS = 5000


def paper_submission_stream(
    groups: List[FactGroup],
    num_contributors: int = PAPER_NUM_CONTRIBUTORS,
    total_submissions: int = PAPER_TOTAL_SUBMISSIONS,
    seed: int = 42,
    cheater_ids: Optional[List[str]] = None,
) -> List[dict]:
    """
    Each event: random fact, random contributor.
    Trust p fixed per contributor; submit ground_truth with prob p else a wrong candidate.
    Cheaters (optional): from event 2000 onward, copy current SOTA (if any).
    """
    rng = random.Random(seed)
    cheater_set = set(cheater_ids or [])
    trusts = {f"C{i}": rng.random() for i in range(num_contributors)}
    events: List[dict] = []

    for i in range(total_submissions):
        g = rng.choice(groups)
        cid = f"C{rng.randint(0, num_contributors - 1)}"
        p = trusts[cid]
        wrong = [c for c in g.candidates if c != g.ground_truth]
        if rng.random() < p or not wrong:
            triple = g.ground_truth
        else:
            triple = rng.choice(wrong)

        events.append(
            {
                "round": i,
                "contributor_id": cid,
                "fact_key": g.fact_key,
                "triple": triple,
                "ground_truth": g.ground_truth,
                "contributor_trust_init": p,
                "cheater_copy": cid in cheater_set and i >= 2000,
                "event_kind": "catalog",
            }
        )
    return events


def build_alpha_paper_events(
    groups: List[FactGroup],
    seed: int = 42,
    *,
    total_submissions: int = PAPER_TOTAL_SUBMISSIONS,
    num_spam_facts: int = 25,
    num_legit_new_facts: int = 15,
) -> List[dict]:
    """
    Full FB13 paper stream (5000 catalog submissions) plus injected spam/legit new F_IDs
    for alpha garbage-collection evaluation.
    """
    events = paper_submission_stream(
        groups, total_submissions=total_submissions, seed=seed
    )
    rng = random.Random(seed + 9001)

    for i in range(num_spam_facts):
        events.append(
            {
                "round": rng.randint(50, total_submissions - 50),
                "contributor_id": f"C{rng.randint(0, PAPER_NUM_CONTRIBUTORS - 1)}",
                "event_kind": "new_fact",
                "is_spam": True,
                "triple": (f"/m/spam_h_{i}", "/r/spam_rel", f"/m/spam_t_{i}"),
                "ground_truth": (f"/m/spam_h_{i}", "/r/spam_rel", f"/m/spam_t_{i}"),
            }
        )

    for i in range(num_legit_new_facts):
        truth = (f"/m/legit_h_{i}", "/r/legit_rel", f"/m/legit_t_{i}")
        r0 = rng.randint(100, total_submissions - 100)
        cids = (
            f"C{rng.randint(0, PAPER_NUM_CONTRIBUTORS - 1)}",
            f"C{rng.randint(0, PAPER_NUM_CONTRIBUTORS - 1)}",
        )
        for j, cid in enumerate(cids):
            events.append(
                {
                    "round": r0 + j,
                    "contributor_id": cid,
                    "event_kind": "new_fact",
                    "fact_local_id": i,
                    "is_spam": False,
                    "triple": truth,
                    "ground_truth": truth,
                }
            )

    return events


def run_paper_alpha_ledger(
    groups: Optional[List[FactGroup]] = None,
    config: Optional[LedgerConfig] = None,
    seed: int = 42,
    *,
    num_spam_facts: int = 25,
    num_legit_new_facts: int = 15,
) -> tuple[CollaborativeKGLedger, Dict[str, Set[int]]]:
    from .runner import run_stream_fb13_mixed

    groups = groups or load_fb13(max_groups=PAPER_NUM_FACTS, pairs_only=True)
    events = build_alpha_paper_events(
        groups,
        seed=seed,
        num_spam_facts=num_spam_facts,
        num_legit_new_facts=num_legit_new_facts,
    )
    return run_stream_fb13_mixed(groups, events, config or LedgerConfig())


def run_paper_ledger(
    groups: Optional[List[FactGroup]] = None,
    config: Optional[LedgerConfig] = None,
    seed: int = 42,
    cheater_ids: Optional[List[str]] = None,
    pairs_path: Optional[str] = None,
    *,
    record_chain: bool = False,
    total_submissions: Optional[int] = None,
    replicated_peers: int = 0,
) -> CollaborativeKGLedger:
    groups = groups or load_fb13(max_groups=PAPER_NUM_FACTS, pairs_only=True, path=pairs_path)
    n_sub = total_submissions if total_submissions is not None else PAPER_TOTAL_SUBMISSIONS
    events = paper_submission_stream(groups, seed=seed, cheater_ids=cheater_ids)
    if n_sub != PAPER_TOTAL_SUBMISSIONS:
        events = events[:n_sub]
    if replicated_peers >= 2:
        from .network import run_stream_fb13_replicated

        network = run_stream_fb13_replicated(groups, events, config or LedgerConfig(), num_peers=replicated_peers)
        network.leader.ledger._sync_report = network.sync_report()  # type: ignore[attr-defined]
        return network.leader.ledger
    return run_stream_fb13(
        groups, events, config or LedgerConfig(), record_chain=record_chain
    )


def ledger_summary(ledger: CollaborativeKGLedger) -> Dict[str, float]:
    confirmed = [f for f in ledger.facts.values() if f.confirmed and not f.recycled]
    return {
        "num_confirmed_facts": len(confirmed),
        "num_recycled": len(ledger.recycled_fact_ids),
        "sota_accuracy": ledger.sota_accuracy(),
        "total_facts": len(ledger.facts),
    }
