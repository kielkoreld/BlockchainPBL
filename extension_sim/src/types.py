from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Triple = Tuple[str, str, str]


@dataclass
class Submission:
    fact_id: int
    contributor_id: str
    triple: Triple
    round_idx: int
    is_follower: bool = False


@dataclass
class SotaChange:
    fact_id: int
    round_idx: int
    old_triple: Optional[Triple]
    new_triple: Triple
    old_quality: float
    new_quality: float


@dataclass
class FactState:
    fact_id: int
    ground_truth: Triple
    sota_triple: Optional[Triple] = None
    sota_quality: float = 0.0
    submissions: List[Submission] = field(default_factory=list)
    triple_qualities: Dict[Triple, float] = field(default_factory=dict)
    contributor_triples: Dict[str, Triple] = field(default_factory=dict)
    created_round: int = 0
    last_activity_round: int = 0
    confirmed: bool = False
    recycled: bool = False
    catalog_fact: bool = False  # pre-seeded FB13 facts: skip garbage F_ID recycling
    sota_history: List[SotaChange] = field(default_factory=list)
