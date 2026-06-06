"""
Ledger + smart-contract logic (Sec. III): TrPublish, CheckVF, garbage F_ID recycling.
Blockchain consensus is omitted; we simulate ordered submissions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .algorithm import evaluate_triple_qualities, follower_quality, pick_sota
from .chain import ChainRecorder, MiniBlockchain
from .types import FactState, SotaChange, Submission, Triple


@dataclass
class LedgerConfig:
    lam: float = 0.5
    alpha: float = 10.0
    min_confirm: int = 2
    kq_iterations: int = 5
    initial_trust: float = 0.7
    # Reduce noisy SOTA oscillation: update only if quality improves by this margin.
    sota_update_margin: float = 0.02


class CollaborativeKGLedger:
    def __init__(
        self,
        config: Optional[LedgerConfig] = None,
        *,
        record_chain: bool = False,
        chain_batch_size: int = 25,
    ):
        self.config = config or LedgerConfig()
        self.facts: Dict[int, FactState] = {}
        self.contributor_trust: Dict[str, float] = {}
        self._contrib_q_history: Dict[str, List[float]] = {}
        self._next_fact_id = 0
        self._submission_intervals: List[int] = []
        self._last_submission_round = 0
        self.recycled_fact_ids: Set[int] = set()
        self.blockchain: Optional[MiniBlockchain] = None
        self._chain_recorder: Optional[ChainRecorder] = None
        if record_chain:
            self.blockchain = MiniBlockchain(batch_size=chain_batch_size)
            self._chain_recorder = ChainRecorder(self.blockchain)

    def register_contributor(self, contributor_id: str, trust: Optional[float] = None):
        if contributor_id not in self.contributor_trust:
            self.contributor_trust[contributor_id] = (
                trust if trust is not None else self.config.initial_trust
            )

    def _avg_submission_interval(self) -> float:
        if len(self._submission_intervals) < 2:
            return 5.0
        return sum(self._submission_intervals) / len(self._submission_intervals)

    def _garbage_window(self) -> int:
        return max(1, int(self.config.alpha * self._avg_submission_interval()))

    def create_fact(
        self, ground_truth: Triple, round_idx: int, *, catalog_fact: bool = False
    ) -> int:
        fid = self._next_fact_id
        self._next_fact_id += 1
        self.facts[fid] = FactState(
            fact_id=fid,
            ground_truth=ground_truth,
            created_round=round_idx,
            last_activity_round=round_idx,
            catalog_fact=catalog_fact,
        )
        return fid

    def submit_triple(
        self,
        contributor_id: str,
        triple: Triple,
        round_idx: int,
        fact_id: Optional[int] = None,
        ground_truth_for_new: Optional[Triple] = None,
    ) -> Optional[int]:
        """Procedure 1–3 simplified: publish, validity/follower check, KQ update."""
        self.register_contributor(contributor_id)
        if self._last_submission_round > 0:
            self._submission_intervals.append(round_idx - self._last_submission_round)
        self._last_submission_round = round_idx

        if fact_id is None:
            if ground_truth_for_new is None:
                ground_truth_for_new = triple
            fact_id = self.create_fact(ground_truth_for_new, round_idx)

        fact = self.facts.get(fact_id)
        if fact is None or fact.recycled:
            return None

        fact.last_activity_round = round_idx
        is_follower = False
        assigned_q: Optional[float] = None

        if fact.sota_triple is not None and triple == fact.sota_triple:
            is_follower = True
            assigned_q = follower_quality(fact.sota_quality, self.config.lam)

        sub = Submission(
            fact_id=fact_id,
            contributor_id=contributor_id,
            triple=triple,
            round_idx=round_idx,
            is_follower=is_follower,
        )
        fact.submissions.append(sub)
        fact.contributor_triples[contributor_id] = triple

        if self._chain_recorder is not None:
            self._chain_recorder.on_publish(
                round_idx,
                fact_id,
                contributor_id,
                triple,
                is_follower,
                contributor_trust=self.contributor_trust.get(contributor_id),
            )

        unique_contributors = {s.contributor_id for s in fact.submissions}
        if len(unique_contributors) >= self.config.min_confirm:
            fact.confirmed = True

        if is_follower:
            fact.triple_qualities[triple] = assigned_q  # type: ignore
            self._update_contributor_trust(contributor_id, assigned_q)  # type: ignore
            self._flush_chain_blocks()
            return fact_id

        self._run_kq_and_update_sota(fact, round_idx)
        self.garbage_collect(round_idx)
        self._flush_chain_blocks()
        return fact_id

    def _flush_chain_blocks(self) -> None:
        if self.blockchain is None:
            return
        while len(self.blockchain.pending) >= self.blockchain.batch_size:
            self.blockchain.mine_pending()

    def _run_kq_and_update_sota(self, fact: FactState, round_idx: int):
        triples: List[Triple] = []
        trusts: List[float] = []
        seen: Set[Triple] = set()
        follower_set: Set[Triple] = set()

        for sub in fact.submissions:
            if sub.triple in seen:
                continue
            seen.add(sub.triple)
            triples.append(sub.triple)
            if sub.is_follower:
                follower_set.add(sub.triple)
                trusts.append(fact.triple_qualities.get(sub.triple, self.contributor_trust[sub.contributor_id]))
            else:
                trusts.append(self.contributor_trust[sub.contributor_id])

        if not triples:
            return

        qualities = evaluate_triple_qualities(
            triples, trusts, num_iterations=self.config.kq_iterations
        )
        if self._chain_recorder is not None:
            self._chain_recorder.on_kq_update(round_idx, fact.fact_id, qualities)
        for t, q in qualities.items():
            if t not in follower_set:
                fact.triple_qualities[t] = q

        for sub in fact.submissions:
            if sub.is_follower:
                continue
            q = fact.triple_qualities.get(sub.triple)
            if q is not None:
                self._update_contributor_trust(sub.contributor_id, q)

        new_sota, new_q = pick_sota(fact.triple_qualities, follower_set)
        old_sota = fact.sota_triple
        old_q = fact.sota_quality
        should_update = False
        if old_sota is None:
            should_update = True
        elif old_sota == new_sota:
            # Same triple: accept only meaningful quality increase.
            should_update = (new_q - old_q) >= self.config.sota_update_margin
        else:
            # Different triple: prevent flip-flop unless challenger clearly better.
            should_update = (new_q - old_q) >= self.config.sota_update_margin

        if should_update:
            if old_sota is not None:
                fact.sota_history.append(
                    SotaChange(
                        fact_id=fact.fact_id,
                        round_idx=round_idx,
                        old_triple=old_sota,
                        new_triple=new_sota,
                        old_quality=fact.sota_quality,
                        new_quality=new_q,
                    )
                )
            if self._chain_recorder is not None:
                self._chain_recorder.on_sota_change(
                    round_idx, fact.fact_id, old_sota, new_sota, old_q, new_q
                )
            fact.sota_triple = new_sota
            fact.sota_quality = new_q

    def _update_contributor_trust(self, contributor_id: str, new_q: float):
        old = self.contributor_trust.get(contributor_id, self.config.initial_trust)
        # Running average over submitted triple qualities (ledger stores history)
        if contributor_id not in self._contrib_q_history:
            self._contrib_q_history[contributor_id] = []
        self._contrib_q_history[contributor_id].append(new_q)
        self.contributor_trust[contributor_id] = sum(self._contrib_q_history[contributor_id]) / len(
            self._contrib_q_history[contributor_id]
        )

    def garbage_collect(self, current_round: int):
        """Sec. III-C: recycle suspicious new F_IDs with too few confirmations."""
        window = self._garbage_window()
        to_recycle = []
        for fid, fact in self.facts.items():
            if fact.confirmed or fact.recycled or fact.catalog_fact:
                continue
            age = current_round - fact.created_round
            if age >= window:
                unique = {s.contributor_id for s in fact.submissions}
                if len(unique) < self.config.min_confirm:
                    to_recycle.append(fid)
        if to_recycle and self._chain_recorder is not None:
            self._chain_recorder.on_garbage_recycle(current_round, to_recycle)
        for fid in to_recycle:
            self.facts[fid].recycled = True
            self.recycled_fact_ids.add(fid)

    def finalize_chain(self) -> None:
        if self.blockchain is not None:
            self.blockchain.finalize()

    def sota_accuracy(self) -> float:
        valid = [f for f in self.facts.values() if f.confirmed and not f.recycled and f.sota_triple]
        if not valid:
            return 0.0
        correct = sum(1 for f in valid if f.sota_triple == f.ground_truth)
        return correct / len(valid)
