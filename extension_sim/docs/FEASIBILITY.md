# 구현 가능성 점검 (블록체인 전공자 대상 설명용)

논문: Wang et al., *Decentralised Knowledge Graph Evolution via Blockchain* (IEEE TSC 2024)

## 1. 블록체인 구현 가능 여부

**결론: 가능 (단, 범위를 나눠야 함)**

| 수준 | 내용 | 1~2주 현실성 |
|------|------|----------------|
| A. 교육용 미니 원장 | 해시 체인, 블록 헤더, TrPublish/CheckVF 이벤트를 블록에 기록, 단일 노드 또는 2~3 노드 P2P | **가능** |
| B. Hyperledger Fabric 축소 | 채널·체인코드·endorsement를 Docker 없이 mock 또는 fabric-samples 최소 네트워크 | **부분 가능** (환경·시간 부담 큼) |
| C. 논문 전체 (10M+ 트리플, 대규모 Fabric) | 원문 실험 규모 | **비현실** (오픈소스 없음, 인프라·데이터 규모 초과) |

현재 `extension_sim`은 **수준 A에 해당하는 오프체인 시뮬**이다. 논문의 스마트 컨트랙트 로직(Alg.1, KQ, SOTA, α·λ)은 Python으로 재현했고, **합의·블록 구조만** 추가하면 “블록체인이 KG 진화를 어떻게 고정·감사하는지”를 비전공자에게 보여줄 수 있다.

권장 데모 경로: `Block { index, prev_hash, txs[] }` + HTML 타임라인(제출 → 검증 → SOTA 변경이 블록 N에 기록됨).

## 2. 지식그래프·SOTA 트리플 시각화 가능 여부

**결론: 가능**

| 대상 | 도구 예 | 설명 |
|------|---------|------|
| KG 서브그래프 | NetworkX + pyvis, 또는 D3/Cytoscape.js | head–relation–tail을 노드/엣지로 표시 |
| SOTA 강조 | 엣지 색·굵기, 라벨 `Q=0.82` | 확정 SOTA vs 후보 트리플 구분 |
| 진화 타임라인 | `sota_history` → 슬라이더/HTML | 라운드별 SOTA 교체 애니메이션 |

FB13 100 fact × 2 triple 규모는 브라우저에서 **즉시 렌더링 가능**하다. 10M 트리플 전체는 샘플링·집계 없이는 불가.

## 3. 현재 시뮬레이터의 위치

- **기여:** 논문 Eq.(3)–(5), Procedure 1–3, λ/α/SOTA **확장 실험** 재현 프레임워크.
- **한계:** Fabric·실네트워크·논문 Table 수치 **1:1 재현은 아님** (공식 코드 없음).
- **구현 완료:** `src/chain.py` + `scripts/build_edu_demo.py` → `results/edu_dashboard.html`
