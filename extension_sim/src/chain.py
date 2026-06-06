"""
Educational mini-blockchain: hash-linked blocks recording TrPublish / CheckVF / UpdateKQ events.

Maps paper Procedures 1–3 (Sec. V) to auditable transactions. No Fabric/consensus — single-node demo.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

Triple = Tuple[str, str, str]


def _triple_str(t: Triple) -> str:
    return f"({t[0]}, {t[1]}, {t[2]})"


@dataclass
class Transaction:
    """One ledger event (paper smart-contract step)."""

    tx_type: str  # TR_PUBLISH | CHECK_VF | UPDATE_KQ | SOTA_CHANGE | GARBAGE_RECYCLE | GENESIS
    round_idx: int
    fact_id: Optional[int] = None
    contributor_id: Optional[str] = None
    triple: Optional[Triple] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.triple is not None:
            d["triple"] = list(self.triple)
        return d


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        body = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "transactions": [t.to_dict() for t in self.transactions],
        }
        raw = json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def seal(self) -> None:
        self.hash = self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "nonce": self.nonce,
            "transactions": [t.to_dict() for t in self.transactions],
        }


class MiniBlockchain:
    """Append-only chain; batches txs every `batch_size` submissions."""

    def __init__(self, batch_size: int = 25, on_block_mined: Optional[Callable[[Block], None]] = None):
        self.batch_size = batch_size
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []
        self._on_block_mined = on_block_mined
        self._init_genesis()

    def _init_genesis(self) -> None:
        g = Block(
            index=0,
            timestamp=0.0,
            transactions=[
                Transaction(
                    tx_type="GENESIS",
                    round_idx=0,
                    payload={"message": "Collaborative KG ledger genesis"},
                )
            ],
            previous_hash="0" * 64,
        )
        g.seal()
        self.chain.append(g)

    @property
    def last_hash(self) -> str:
        return self.chain[-1].hash

    def add_transaction(self, tx: Transaction) -> None:
        self.pending.append(tx)

    def try_mine_pending(self) -> Optional[Block]:
        if len(self.pending) >= self.batch_size:
            return self.mine_pending()
        return None

    def mine_pending(self) -> Optional[Block]:
        if not self.pending:
            return None
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=list(self.pending),
            previous_hash=self.last_hash,
        )
        block.seal()
        self.chain.append(block)
        self.pending.clear()
        if self._on_block_mined is not None:
            self._on_block_mined(block)
        return block

    def finalize(self) -> None:
        """Flush remaining pending txs into a final block."""
        while self.pending:
            self.mine_pending()

    def to_dict(self) -> dict:
        self.finalize()
        return {
            "length": len(self.chain),
            "blocks": [b.to_dict() for b in self.chain],
        }

    def verify_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            prev, cur = self.chain[i - 1], self.chain[i]
            if cur.previous_hash != prev.hash:
                return False
            if cur.hash != cur.compute_hash():
                return False
        return True


class ChainRecorder:
    """Hooks paper procedures to blockchain transactions."""

    def __init__(self, chain: MiniBlockchain):
        self.chain = chain

    def on_publish(
        self,
        round_idx: int,
        fact_id: int,
        contributor_id: str,
        triple: Triple,
        is_follower: bool,
        contributor_trust: Optional[float] = None,
    ) -> None:
        pub_payload: Dict[str, Any] = {"procedure": "TrPublish (Procedure 1)"}
        if contributor_trust is not None:
            pub_payload["contributor_trust"] = contributor_trust
        self.chain.add_transaction(
            Transaction(
                tx_type="TR_PUBLISH",
                round_idx=round_idx,
                fact_id=fact_id,
                contributor_id=contributor_id,
                triple=triple,
                payload=pub_payload,
            )
        )
        self.chain.add_transaction(
            Transaction(
                tx_type="CHECK_VF",
                round_idx=round_idx,
                fact_id=fact_id,
                contributor_id=contributor_id,
                triple=triple,
                payload={
                    "procedure": "CheckVF (Procedure 2)",
                    "is_follower": is_follower,
                    "valid": True,
                },
            )
        )

    def on_kq_update(
        self,
        round_idx: int,
        fact_id: int,
        qualities: Dict[Triple, float],
    ) -> None:
        self.chain.add_transaction(
            Transaction(
                tx_type="UPDATE_KQ",
                round_idx=round_idx,
                fact_id=fact_id,
                payload={
                    "procedure": "UpdateKQ (Procedure 3)",
                    "qualities": {_triple_str(k): round(v, 4) for k, v in qualities.items()},
                },
            )
        )

    def on_sota_change(
        self,
        round_idx: int,
        fact_id: int,
        old_triple: Optional[Triple],
        new_triple: Triple,
        old_q: float,
        new_q: float,
    ) -> None:
        self.chain.add_transaction(
            Transaction(
                tx_type="SOTA_CHANGE",
                round_idx=round_idx,
                fact_id=fact_id,
                triple=new_triple,
                payload={
                    "old_triple": list(old_triple) if old_triple else None,
                    "new_triple": list(new_triple),
                    "old_quality": round(old_q, 4),
                    "new_quality": round(new_q, 4),
                },
            )
        )

    def on_garbage_recycle(self, round_idx: int, fact_ids: List[int]) -> None:
        if not fact_ids:
            return
        self.chain.add_transaction(
            Transaction(
                tx_type="GARBAGE_RECYCLE",
                round_idx=round_idx,
                payload={"recycled_f_ids": fact_ids, "alpha_window": "applied"},
            )
        )
