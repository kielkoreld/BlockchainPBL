"""
Peer nodes: replay block transactions to keep ledger state in sync (MongoDB oplog-style).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .chain import Block, MiniBlockchain, Transaction
from .ledger import CollaborativeKGLedger, LedgerConfig
from .types import Triple


def ledger_state_digest(ledger: CollaborativeKGLedger) -> str:
    """Deterministic hash of SOTA + trust state for cross-peer comparison."""
    parts: List[tuple] = []
    for fid in sorted(ledger.facts.keys()):
        f = ledger.facts[fid]
        if f.recycled:
            parts.append(("f", fid, "recycled"))
            continue
        sota = list(f.sota_triple) if f.sota_triple else None
        parts.append(
            (
                "f",
                fid,
                sota,
                round(f.sota_quality, 4),
                f.confirmed,
            )
        )
    for cid in sorted(ledger.contributor_trust.keys()):
        parts.append(("c", cid, round(ledger.contributor_trust[cid], 4)))
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def replay_transaction(ledger: CollaborativeKGLedger, tx: Transaction) -> None:
    """Apply one chain tx to a follower ledger (TR_PUBLISH drives state; others are audit)."""
    if tx.tx_type == "TR_PUBLISH":
        if tx.contributor_id is None or tx.fact_id is None or tx.triple is None:
            return
        trust = tx.payload.get("contributor_trust")
        if tx.contributor_id not in ledger.contributor_trust:
            ledger.register_contributor(
                tx.contributor_id, float(trust) if trust is not None else None
            )
        elif trust is not None:
            # Snapshot trust at publish time (leader state before this submit).
            ledger.contributor_trust[tx.contributor_id] = float(trust)
        ledger.submit_triple(
            tx.contributor_id,
            tuple(tx.triple),
            tx.round_idx,
            fact_id=tx.fact_id,
        )
    elif tx.tx_type == "GARBAGE_RECYCLE":
        for fid in tx.payload.get("recycled_f_ids", []):
            fact = ledger.facts.get(fid)
            if fact is not None:
                fact.recycled = True
                ledger.recycled_fact_ids.add(fid)


@dataclass
class PeerNode:
    peer_id: int
    ledger: CollaborativeKGLedger
    blockchain: MiniBlockchain
    is_leader: bool = False

    @property
    def state_digest(self) -> str:
        return ledger_state_digest(self.ledger)

    def receive_block(self, block: Block) -> None:
        if block.previous_hash != self.blockchain.last_hash:
            raise ValueError(
                f"Peer {self.peer_id}: block #{block.index} prev_hash mismatch"
            )
        if block.hash != block.compute_hash():
            raise ValueError(f"Peer {self.peer_id}: block #{block.index} hash invalid")
        self.blockchain.chain.append(block)
        for tx in block.transactions:
            if tx.tx_type in ("TR_PUBLISH", "GARBAGE_RECYCLE"):
                replay_transaction(self.ledger, tx)


def verify_peers_in_sync(peers: List[PeerNode]) -> Dict[str, object]:
    digests = [p.state_digest for p in peers]
    chain_lens = [len(p.blockchain.chain) for p in peers]
    chains_valid = [p.blockchain.verify_chain() for p in peers]
    return {
        "num_peers": len(peers),
        "state_digests": {f"peer_{p.peer_id}": p.state_digest for p in peers},
        "all_states_match": len(set(digests)) == 1,
        "chain_lengths": chain_lens,
        "all_chain_lengths_match": len(set(chain_lens)) == 1,
        "all_chains_valid": all(chains_valid),
        "in_sync": len(set(digests)) == 1 and len(set(chain_lens)) == 1 and all(chains_valid),
    }
