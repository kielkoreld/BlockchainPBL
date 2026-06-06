"""Mini-blockchain tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chain import MiniBlockchain, Transaction
from src.ledger import CollaborativeKGLedger, LedgerConfig


def test_chain_links_and_verify():
    chain = MiniBlockchain(batch_size=2)
    chain.add_transaction(Transaction("TR_PUBLISH", 1, fact_id=0, payload={"a": 1}))
    chain.add_transaction(Transaction("CHECK_VF", 1, fact_id=0, payload={"b": 2}))
    chain.finalize()
    assert len(chain.chain) >= 2
    assert chain.verify_chain()
    assert chain.chain[1].previous_hash == chain.chain[0].hash


def test_ledger_records_chain():
    ledger = CollaborativeKGLedger(LedgerConfig(), record_chain=True, chain_batch_size=5)
    fid = ledger.create_fact(("h", "r", "t"), 0, catalog_fact=True)
    ledger.submit_triple("C0", ("h", "r", "t"), 1, fact_id=fid)
    ledger.submit_triple("C1", ("h", "r", "t2"), 2, fact_id=fid)
    ledger.finalize_chain()
    assert ledger.blockchain is not None
    assert ledger.blockchain.verify_chain()
    assert len(ledger.blockchain.pending) == 0


def run_all():
    test_chain_links_and_verify()
    test_ledger_records_chain()
    print("All chain tests passed.")


if __name__ == "__main__":
    run_all()
