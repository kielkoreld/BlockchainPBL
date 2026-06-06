"""
3-peer network: leader writes + mines blocks; followers replay blocks to sync ledger state.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .chain import Block, MiniBlockchain
from .fb13 import FactGroup
from .ledger import CollaborativeKGLedger, LedgerConfig
from .peer import PeerNode, verify_peers_in_sync
from .runner import _sort_events


class PeerNetwork:
    NUM_PEERS = 3

    def __init__(
        self,
        config: Optional[LedgerConfig] = None,
        chain_batch_size: int = 25,
        num_peers: int = NUM_PEERS,
    ):
        self.config = config or LedgerConfig()
        self.peers: List[PeerNode] = []
        for i in range(num_peers):
            is_leader = i == 0
            ledger = CollaborativeKGLedger(
                self.config,
                record_chain=is_leader,
                chain_batch_size=chain_batch_size,
            )
            chain = ledger.blockchain if is_leader else MiniBlockchain(batch_size=chain_batch_size)
            assert chain is not None
            if is_leader:
                chain._on_block_mined = self._on_leader_block  # type: ignore[attr-defined]
            self.peers.append(PeerNode(i, ledger, chain, is_leader=is_leader))
        self.leader = self.peers[0]

    def _on_leader_block(self, block: Block) -> None:
        for peer in self.peers[1:]:
            peer.receive_block(block)

    def init_catalog(self, groups: List[FactGroup]) -> Dict[tuple, int]:
        key_to_fid: Dict[tuple, int] = {}
        for g in groups:
            fid = self.leader.ledger.create_fact(g.ground_truth, 0, catalog_fact=True)
            for peer in self.peers[1:]:
                peer.ledger.create_fact(g.ground_truth, 0, catalog_fact=True)
            key_to_fid[g.fact_key] = fid
        return key_to_fid

    def leader_submit(
        self,
        contributor_id: str,
        triple: tuple,
        round_idx: int,
        fact_id: int,
        trust: Optional[float] = None,
    ) -> None:
        if trust is not None:
            self.leader.ledger.register_contributor(contributor_id, trust)
        self.leader.ledger.submit_triple(contributor_id, triple, round_idx, fact_id=fact_id)

    def finalize(self) -> None:
        self.leader.ledger.finalize_chain()

    def sync_report(self) -> Dict[str, object]:
        return verify_peers_in_sync(self.peers)


def run_stream_fb13_replicated(
    groups: List[FactGroup],
    events: List[dict],
    config: Optional[LedgerConfig] = None,
    *,
    chain_batch_size: int = 25,
    num_peers: int = 3,
) -> PeerNetwork:
    network = PeerNetwork(config, chain_batch_size=chain_batch_size, num_peers=num_peers)
    key_to_fid = network.init_catalog(groups)

    for item in _sort_events(events):
        if item.get("event_kind", "catalog") != "catalog":
            continue
        cid = item["contributor_id"]
        trust = item.get("contributor_trust_init")
        fid = key_to_fid[item["fact_key"]]
        triple = tuple(item["triple"])
        fact = network.leader.ledger.facts[fid]
        if item.get("cheater_copy") and fact.sota_triple is not None:
            triple = fact.sota_triple
        network.leader_submit(cid, triple, item["round"], fid, trust=trust)

    network.finalize()
    return network
