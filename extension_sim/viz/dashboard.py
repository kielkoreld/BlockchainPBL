"""
Generate standalone HTML dashboard: mini-blockchain + KG/SOTA graph (vis-network CDN).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.chain import MiniBlockchain
from src.ledger import CollaborativeKGLedger

ROOT = Path(__file__).resolve().parents[1]


def _short(s: str, n: int = 24) -> str:
    s = s.replace("/m/", "").replace("/r/", "")
    return s if len(s) <= n else s[: n - 2] + ".."


def _entity_id(uri: str) -> str:
    return f"e:{uri}"


def collect_kg_graph(
    ledger: CollaborativeKGLedger,
    max_facts: int = 50,
) -> Dict[str, Any]:
    """
    SOTA KG: entities merged by URI; relation on edge label (RDF-style).
    Candidates kept in per-fact detail for drill-down.
    """
    facts = [
        f
        for f in ledger.facts.values()
        if f.confirmed and not f.recycled and f.sota_triple
    ]
    facts.sort(key=lambda f: f.fact_id)
    all_facts = facts
    display_facts = facts[:max_facts]

    entity_degree: Dict[str, int] = {}
    nodes: Dict[str, dict] = {}
    sota_edges: List[dict] = []
    fact_details: Dict[int, dict] = {}

    def bump_entity(eid: str, label: str) -> None:
        entity_degree[eid] = entity_degree.get(eid, 0) + 1
        if eid not in nodes:
            nodes[eid] = {
                "id": eid,
                "label": label,
                "group": "entity",
                "title": eid.replace("e:", ""),
            }

    for f in display_facts:
        h, r, t = f.sota_triple  # type: ignore
        hid, tid = _entity_id(h), _entity_id(t)
        bump_entity(hid, _short(h))
        bump_entity(tid, _short(t))
        correct = f.sota_triple == f.ground_truth
        color = "#2e7d32" if correct else "#c62828"
        sota_edges.append(
            {
                "id": f"sota-{f.fact_id}",
                "from": hid,
                "to": tid,
                "label": _short(r, 14),
                "title": (
                    f"F{f.fact_id} SOTA\n(h,r,t)\nQ={f.sota_quality:.3f}\n"
                    f"{'정답' if correct else '오답'}"
                ),
                "arrows": "to",
                "color": {"color": color, "highlight": color},
                "width": 2 + min(f.sota_quality, 1.0) * 2,
                "font": {"size": 11, "align": "horizontal", "color": color},
                "smooth": {"type": "curvedCW", "roundness": 0.15},
            }
        )

        detail_nodes: List[dict] = []
        detail_edges: List[dict] = []
        dhid, dtid_sota = hid, tid
        detail_nodes.append({"id": dhid, "label": _short(h, 18), "group": "head"})
        detail_nodes.append({"id": dtid_sota, "label": _short(t, 18), "group": "tail"})
        detail_edges.append(
            {
                "id": f"d-sota-{f.fact_id}",
                "from": dhid,
                "to": dtid_sota,
                "label": _short(r, 12) + " (SOTA)",
                "color": color,
                "width": 3,
                "arrows": "to",
            }
        )
        for cand, q in f.triple_qualities.items():
            if cand == f.sota_triple:
                continue
            _, _, ct = cand
            dtid_c = _entity_id(ct)
            if dtid_c not in {n["id"] for n in detail_nodes}:
                detail_nodes.append({"id": dtid_c, "label": _short(ct, 18), "group": "candidate"})
            detail_edges.append(
                {
                    "id": f"d-cand-{f.fact_id}-{_short(ct,8)}",
                    "from": dhid,
                    "to": dtid_c,
                    "label": f"candidate Q={q:.2f}",
                    "color": "#9e9e9e",
                    "width": 1,
                    "dashes": True,
                    "arrows": "to",
                }
            )
        fact_details[f.fact_id] = {
            "fact_id": f.fact_id,
            "nodes": detail_nodes,
            "edges": detail_edges,
            "head": _short(f.ground_truth[0]),
            "relation": _short(f.ground_truth[1]),
            "sota_tail": _short(t),
            "truth_tail": _short(f.ground_truth[2]),
            "correct": correct,
            "sota_q": round(f.sota_quality, 3),
            "changes": len(f.sota_history),
        }

    for eid, deg in entity_degree.items():
        nodes[eid]["size"] = 12 + min(deg, 8) * 3
        if deg >= 2:
            nodes[eid]["group"] = "hub"

    return {
        "nodes": list(nodes.values()),
        "edges": sota_edges,
        "entity_count": len(nodes),
        "sota_edge_count": len(sota_edges),
        "shared_entities": sum(1 for d in entity_degree.values() if d >= 2),
        "fact_summaries": [fact_details[f.fact_id] for f in display_facts if f.fact_id in fact_details],
        "fact_details": fact_details,
        "total_sota_facts": len(all_facts),
        "displayed_facts": len(display_facts),
    }


def collect_sota_timeline(ledger: CollaborativeKGLedger, max_facts: int = 30) -> List[dict]:
    rows = []
    for f in ledger.facts.values():
        if not f.sota_history:
            continue
        for ch in f.sota_history[:max_facts]:
            rows.append(
                {
                    "fact_id": ch.fact_id,
                    "round": ch.round_idx,
                    "old": list(ch.old_triple) if ch.old_triple else None,
                    "new": list(ch.new_triple),
                    "new_q": round(ch.new_quality, 3),
                }
            )
    rows.sort(key=lambda x: x["round"])
    return rows[:500]


def render_dashboard(
    ledger: CollaborativeKGLedger,
    chain: Optional[MiniBlockchain],
    out_path: Path,
    title: str = "DKG-Blockchain 교육용 데모",
    sync_report: Optional[Dict[str, object]] = None,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if chain is None:
        chain = ledger.blockchain
    chain_data = chain.to_dict() if chain else {"length": 0, "blocks": []}

    kg = collect_kg_graph(ledger)
    timeline = collect_sota_timeline(ledger)
    summary = {
        "confirmed": sum(1 for f in ledger.facts.values() if f.confirmed and not f.recycled),
        "sota_accuracy": round(ledger.sota_accuracy(), 4),
        "contributors": len(ledger.contributor_trust),
        "blocks": chain_data["length"],
        "chain_valid": chain.verify_chain() if chain else False,
        "kg_entities": kg["entity_count"],
        "kg_sota_edges": kg["sota_edge_count"],
        "shared_entities": kg["shared_entities"],
    }
    if sync_report:
        summary["peers_in_sync"] = sync_report.get("in_sync", False)
        summary["num_peers"] = sync_report.get("num_peers", 0)

    payload = json.dumps(
        {
            "title": title,
            "summary": summary,
            "sync": sync_report or {},
            "chain": chain_data,
            "kg": kg,
            "timeline": timeline,
        },
        ensure_ascii=False,
    )

    html = _HTML_TEMPLATE.replace("__DATA_JSON__", payload)
    out_path.write_text(html, encoding="utf-8")
    return out_path


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <title>DKG Blockchain Demo</title>
  <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }
    header { background: #1a237e; color: #fff; padding: 1rem 1.5rem; }
    header h1 { margin: 0; font-size: 1.25rem; }
    .stats { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; font-size: 0.85rem; }
    .stats span { background: rgba(255,255,255,0.15); padding: 0.25rem 0.6rem; border-radius: 4px; }
    nav { display: flex; gap: 0; background: #fff; border-bottom: 1px solid #ddd; flex-wrap: wrap; }
    nav button { flex: 1; min-width: 120px; padding: 0.75rem; border: none; background: #fff; cursor: pointer; font-size: 0.9rem; }
    nav button.active { border-bottom: 3px solid #1a237e; font-weight: 600; color: #1a237e; }
    .panel { display: none; padding: 1rem 1.5rem; }
    .panel.active { display: block; }
    .graph-row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .graph-box { flex: 1; min-width: 280px; }
    #kg-network, #detail-network { height: 480px; border: 1px solid #ccc; background: #fff; border-radius: 8px; }
    .legend { font-size: 0.85rem; color: #444; margin-bottom: 0.5rem; line-height: 1.5; }
    .legend b.green { color: #2e7d32; } .legend b.red { color: #c62828; }
    .controls { margin: 0.5rem 0 1rem; display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    select { padding: 0.35rem 0.5rem; font-size: 0.9rem; }
    table { width: 100%; border-collapse: collapse; background: #fff; font-size: 0.85rem; }
    th, td { border: 1px solid #ddd; padding: 0.4rem 0.5rem; text-align: left; }
    th { background: #eee; }
    .block { background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 0.75rem; padding: 0.75rem; }
    .block h3 { margin: 0 0 0.5rem; font-size: 1rem; color: #1a237e; }
    .hash { font-family: monospace; font-size: 0.75rem; word-break: break-all; color: #555; }
    .tx { font-size: 0.8rem; padding: 0.35rem 0; border-top: 1px solid #eee; }
    .tx-type { font-weight: 600; color: #1565c0; }
    .sync-ok { color: #2e7d32; font-weight: 600; }
    .sync-fail { color: #c62828; font-weight: 600; }
    .peer-card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem; font-size: 0.85rem; }
  </style>
</head>
<body>
  <header>
    <h1 id="page-title">DKG-Blockchain Demo</h1>
    <div class="stats" id="summary-stats"></div>
  </header>
  <nav>
    <button type="button" class="active" data-tab="sync">노드 동기화</button>
    <button type="button" data-tab="chain">블록체인</button>
    <button type="button" data-tab="kg">SOTA KG</button>
    <button type="button" data-tab="evo">SOTA 진화</button>
  </nav>

  <section id="tab-sync" class="panel active">
    <p>리더(Peer 0)가 블록을 생성하면 Follower(Peer 1, 2)가 <strong>TR_PUBLISH</strong> 트랜잭션을 replay해 동일 원장 상태를 재구성합니다 (MongoDB oplog replay와 유사).</p>
    <div id="sync-status"></div>
    <div id="peer-cards"></div>
  </section>

  <section id="tab-chain" class="panel">
    <p>TrPublish → CheckVF → UpdateKQ / SOTA_CHANGE 이벤트가 블록에 기록됩니다.</p>
    <div id="blocks-list"></div>
  </section>

  <section id="tab-kg" class="panel">
    <p class="legend">
      <b class="green">녹색 화살표</b> = 정답 SOTA (head → tail, 라벨=relation) ·
      <b class="red">빨간 화살표</b> = 오답 SOTA ·
      <b>큰 노드</b> = 여러 fact와 연결된 공유 엔티티
    </p>
    <div class="controls">
      <label>F_ID 상세: <select id="fact-select"></select></label>
      <span id="kg-meta"></span>
    </div>
    <div class="graph-row">
      <div class="graph-box">
        <h3>SOTA 지식 그래프 (전체)</h3>
        <div id="kg-network"></div>
      </div>
      <div class="graph-box">
        <h3>선택 fact: SOTA vs 후보</h3>
        <div id="detail-network"></div>
      </div>
    </div>
    <h3 style="margin-top:1rem">SOTA 트리플 목록</h3>
    <table id="fact-table"><thead><tr><th>F_ID</th><th>head</th><th>relation</th><th>SOTA tail</th><th>truth tail</th><th>Q</th><th>변경</th><th>정답</th></tr></thead><tbody></tbody></table>
  </section>

  <section id="tab-evo" class="panel">
    <p>SOTA 교체 이벤트 (최대 500건)</p>
    <table id="timeline-table"><thead><tr><th>round</th><th>F_ID</th><th>new tail</th><th>Q</th></tr></thead><tbody></tbody></table>
  </section>

  <script>
    const DATA = __DATA_JSON__;
    document.getElementById('page-title').textContent = DATA.title;
    const s = DATA.summary;
    const syncOk = s.peers_in_sync;
    document.getElementById('summary-stats').innerHTML = [
      ['확정 사실', s.confirmed],
      ['SOTA 정확도', (s.sota_accuracy * 100).toFixed(1) + '%'],
      ['KG 엔티티', s.kg_entities],
      ['SOTA 엣지', s.kg_sota_edges],
      ['공유 엔티티', s.shared_entities],
      ['Peer 동기화', syncOk === undefined ? 'N/A' : (syncOk ? 'OK' : 'FAIL')],
      ['블록', s.blocks],
    ].map(([k,v]) => `<span>${k}: ${v}</span>`).join('');

    document.querySelectorAll('nav button').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      });
    });

    // --- Sync tab ---
    const syncDiv = document.getElementById('sync-status');
    const peerCards = document.getElementById('peer-cards');
    if (DATA.sync && DATA.sync.num_peers) {
      const ok = DATA.sync.in_sync;
      syncDiv.innerHTML = `<p class="${ok ? 'sync-ok' : 'sync-fail'}">${ok ? '3개 노드 원장·체인 동기화 성공' : '동기화 실패 — state digest 불일치'}</p>`;
      Object.entries(DATA.sync.state_digests || {}).forEach(([pid, dig]) => {
        const card = document.createElement('div');
        card.className = 'peer-card';
        card.innerHTML = `<strong>${pid}</strong><br/>state digest: <code>${dig}</code>`;
        peerCards.appendChild(card);
      });
    } else {
      syncDiv.innerHTML = '<p>동기화 데이터 없음 (replicated_peers 모드로 데모 실행 필요)</p>';
    }

    // --- Chain tab ---
    const bl = document.getElementById('blocks-list');
    DATA.chain.blocks.forEach(b => {
      const div = document.createElement('div');
      div.className = 'block';
      const txs = b.transactions.map(t => {
        const triple = t.triple ? ` ${JSON.stringify(t.triple)}` : '';
        return `<div class="tx"><span class="tx-type">${t.tx_type}</span> r=${t.round_idx} C=${t.contributor_id||'-'} F=${t.fact_id??'-'}${triple}</div>`;
      }).join('');
      div.innerHTML = `<h3>Block #${b.index}</h3><div class="hash">hash: ${b.hash}</div><div>tx: ${b.transactions.length}</div>${txs}`;
      bl.appendChild(div);
    });

    // --- KG tab ---
    document.getElementById('kg-meta').textContent =
      `표시 ${DATA.kg.displayed_facts}/${DATA.kg.total_sota_facts} facts`;

    const netOpts = {
      physics: { barnesHut: { gravitationalConstant: -6000, springLength: 120 }, stabilization: { iterations: 120 } },
      edges: { font: { size: 11, align: 'middle' }, smooth: { type: 'dynamic' } },
      nodes: { font: { size: 12 } },
      groups: {
        entity: { color: { background: '#e3f2fd', border: '#1565c0' }, shape: 'dot' },
        hub: { color: { background: '#bbdefb', border: '#0d47a1' }, shape: 'dot', borderWidth: 2 },
        head: { color: { background: '#e8eaf6', border: '#3949ab' }, shape: 'dot', size: 20 },
        tail: { color: { background: '#e8f5e9', border: '#2e7d32' }, shape: 'dot', size: 18 },
        candidate: { color: { background: '#fafafa', border: '#9e9e9e' }, shape: 'dot', size: 14 },
      },
      interaction: { hover: true, tooltipDelay: 100 },
    };

    const kgNet = new vis.Network(
      document.getElementById('kg-network'),
      { nodes: new vis.DataSet(DATA.kg.nodes), edges: new vis.DataSet(DATA.kg.edges) },
      netOpts
    );

    const detailNetEl = document.getElementById('detail-network');
    let detailNet = null;
    const factSelect = document.getElementById('fact-select');
    const details = DATA.kg.fact_details || {};
    Object.keys(details).sort((a,b)=>+a - +b).forEach(fid => {
      const opt = document.createElement('option');
      opt.value = fid;
      opt.textContent = `F${fid} (${details[fid].correct ? 'O' : 'X'})`;
      factSelect.appendChild(opt);
    });

    function showDetail(fid) {
      const d = details[fid];
      if (!d) return;
      const data = { nodes: new vis.DataSet(d.nodes), edges: new vis.DataSet(d.edges) };
      if (detailNet) detailNet.destroy();
      detailNet = new vis.Network(detailNetEl, data, {
        ...netOpts,
        physics: { enabled: false },
        layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', nodeSpacing: 150 } },
      });
    }
    if (factSelect.options.length) {
      showDetail(factSelect.value);
      factSelect.addEventListener('change', () => showDetail(factSelect.value));
    }

    const ftb = document.querySelector('#fact-table tbody');
    DATA.kg.fact_summaries.forEach(r => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.innerHTML = `<td>${r.fact_id}</td><td>${r.head}</td><td>${r.relation}</td>
        <td>${r.sota_tail}</td><td>${r.truth_tail}</td><td>${r.sota_q}</td>
        <td>${r.changes}</td><td style="color:${r.correct?'green':'red'}">${r.correct?'O':'X'}</td>`;
      tr.addEventListener('click', () => { factSelect.value = r.fact_id; showDetail(r.fact_id); });
      ftb.appendChild(tr);
    });

    const ttb = document.querySelector('#timeline-table tbody');
    DATA.timeline.forEach(r => {
      const tr = document.createElement('tr');
      const tail = r.new ? r.new[2] : '';
      tr.innerHTML = `<td>${r.round}</td><td>${r.fact_id}</td><td>${tail}</td><td>${r.new_q}</td>`;
      ttb.appendChild(tr);
    });
  </script>
</body>
</html>
"""
