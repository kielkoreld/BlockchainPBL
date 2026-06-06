from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .fb13 import FactGroup
from .ledger import CollaborativeKGLedger, LedgerConfig


def _sort_events(events: List[dict]) -> List[dict]:
    """Stable order: round, then insertion sequence (deterministic replay)."""
    for i, item in enumerate(events):
        if "_seq" not in item:
            item["_seq"] = i
    return sorted(events, key=lambda x: (x["round"], x["_seq"]))


def run_stream_fb13(
    groups: List[FactGroup],
    events: List[dict],
    config: Optional[LedgerConfig] = None,
    *,
    record_chain: bool = False,
) -> CollaborativeKGLedger:
    ledger = CollaborativeKGLedger(config, record_chain=record_chain)
    key_to_fid: Dict[tuple, int] = {}

    for g in groups:
        fid = ledger.create_fact(g.ground_truth, 0, catalog_fact=True)
        key_to_fid[g.fact_key] = fid

    for item in _sort_events(events):
        cid = item["contributor_id"]
        trust = item.get("contributor_trust_init")
        ledger.register_contributor(cid, trust)
        fid = key_to_fid[item["fact_key"]]
        triple = tuple(item["triple"])
        fact = ledger.facts[fid]
        if item.get("cheater_copy") and fact.sota_triple is not None:
            triple = fact.sota_triple
        ledger.submit_triple(cid, triple, item["round"], fact_id=fid)

    ledger.finalize_chain()
    return ledger


def run_stream_fb13_mixed(
    groups: List[FactGroup],
    events: List[dict],
    config: Optional[LedgerConfig] = None,
    *,
    record_chain: bool = False,
) -> Tuple[CollaborativeKGLedger, Dict[str, Set[int]]]:
    """
    Catalog submissions (paper stream) plus optional new-fact spam/legit events.
    Returns ledger and {spam_fids, legit_new_fids}.
    """
    ledger = CollaborativeKGLedger(config, record_chain=record_chain)
    key_to_fid: Dict[tuple, int] = {}
    local_to_fid: Dict[int, int] = {}
    spam_fids: Set[int] = set()
    legit_new_fids: Set[int] = set()

    for g in groups:
        fid = ledger.create_fact(g.ground_truth, 0, catalog_fact=True)
        key_to_fid[g.fact_key] = fid

    for item in _sort_events(events):
        cid = item["contributor_id"]
        trust = item.get("contributor_trust_init")
        ledger.register_contributor(cid, trust)
        kind = item.get("event_kind", "catalog")

        if kind == "catalog":
            fid = key_to_fid[item["fact_key"]]
            triple = tuple(item["triple"])
            fact = ledger.facts[fid]
            if item.get("cheater_copy") and fact.sota_triple is not None:
                triple = fact.sota_triple
            ledger.submit_triple(cid, triple, item["round"], fact_id=fid)
            continue

        triple = tuple(item["triple"])
        local_id = item.get("fact_local_id")
        if local_id is not None:
            if local_id not in local_to_fid:
                fid = ledger.submit_triple(
                    cid,
                    triple,
                    item["round"],
                    ground_truth_for_new=item.get("ground_truth", triple),
                )
                if fid is None:
                    continue
                local_to_fid[local_id] = fid
                if item.get("is_spam"):
                    spam_fids.add(fid)
                else:
                    legit_new_fids.add(fid)
            else:
                ledger.submit_triple(
                    cid, triple, item["round"], fact_id=local_to_fid[local_id]
                )
        else:
            fid = ledger.submit_triple(
                cid,
                triple,
                item["round"],
                ground_truth_for_new=item.get("ground_truth", triple),
            )
            if fid is not None and item.get("is_spam"):
                spam_fids.add(fid)

    ledger.finalize_chain()
    return ledger, {"spam_fids": spam_fids, "legit_new_fids": legit_new_fids}
