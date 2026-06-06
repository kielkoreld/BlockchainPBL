# 논문 vs 현재 구현 상태 (상세 대조)

**논문:** Wang et al., *Decentralised Knowledge Graph Evolution via Blockchain*, IEEE TSC 17(1), 2024  
**구현:** `extension_sim/` (Python, 오프체인 시뮬 + 교육용 미니 블록체인 + HTML 대시보드)

---

## 1. 한눈에 보는 완성도

| 영역 | 논문 | 구현 상태 | 대략적 완성도 |
|------|------|-----------|---------------|
| **IV. KQ 알고리즘 (Alg.1, 식 3–5)** | 핵심 기여 | `src/algorithm.py` + 단위 테스트 | **~95%** |
| **III-C 스마트 컨트랙트 로직** | TrPublish, CheckVF, UpdateKQ | `src/ledger.py` 단일 프로세스 | **~70%** |
| **III-C Follower (λ)** | Q = λ·Q_ST | 구현 + λ ablation | **~90%** |
| **III-C 쓰레기 F_ID (α)** | α×평균 간격 | 구현 + α ablation (스팸 시나리오) | **~75%** |
| **III-B 원장 KV 구조** | E_ID, R_ID, F_ID, SOTA, 중복 인덱스 | 문자열 트리플·fact_id만 | **~25%** |
| **III-A 합의 / Fabric** | PBFT, endorser, 블록 검증 | 미니 해시 체인 (교육용) | **~15%** |
| **V Fabric 배포·체인코드** | Go chaincode, 10M 트리플 | 없음 | **0%** |
| **VI-B FB13 실험** | 100 facts, 5000 제출 등 | FB13 paper TSV + 동일 규모 시뮬 | **~60%** |
| **VI 비교·MKPB/WMCA** | Algorithm 2·3 비교 | 미구현 | **0%** |
| **VI FB2M·표 VI** | 2M 엔티티, 10M 트리플 | 미구현 | **0%** |
| **확장 (goal.txt)** | λ·α·SOTA 진화 | 3개 실험 스크립트 | **~85%** |
| **교육 확장** | — | 블록체인 HTML + KG/SOTA 시각화 | **신규** |

**전체 프레임워크 재현:** 약 **35–40%** (핵심 *품질 평가·follower·SOTA 선정*은 높고, *분산 인프라·대규모 실험*은 낮음).

---

## 2. 섹션별 상세 대조

### 2.1 III-A 프레임워크 개요 · 합의

| 논문 요소 | 구현 |
|-----------|------|
| 트랜잭션 개시 → endorser → SOTA 갱신 | `submit_triple` 한 함수에서 순차 처리 |
| Primary/backup, prepare/commit, 2/3 다수 | **없음** |
| 블록 검증 후 원장 갱신 | `MiniBlockchain`: SHA-256 해시 체인, 배치 블록 (`src/chain.py`) |
| 발행 트리플 불변성 | 체인에 이벤트 기록 → **변조 탐지는 단일 노드 검증** 수준 |

**설명:** 블록체인 전공자에게 “무엇이 블록에 들어가는지”는 `results/edu_dashboard.html` 첫 탭으로 보여 줄 수 있으나, **분산 합의·Fabric은 재현하지 않음**.

---

### 2.2 III-B 원장 설계

| 논문 KV | 구현 |
|---------|------|
| E_ID - E_NAME, R_ID - R_NAME | Freebase `/m/`, `/r/` **문자열 그대로** (숫자 ID 없음) |
| SOTA: F_ID → (E_ID, R_ID, E_ID) | `FactState.sota_triple` + `fact_id` |
| 모든 트리플: F_ID → {C_ID} | `FactState.submissions`, `contributor_triples` |
| Entity/Relation → {F_ID} 중복 인덱스 | **없음** (head, relation으로 `FactGroup`만) |
| 기여자: C_ID → {F_ID → (…, Q)} | `contributor_trust`, `triple_qualities` (분리 저장) |
| F_FLAG, CRD, PT_NUM, P_TIME (표 IV) | **미구현** |

---

### 2.3 III-C 스마트 컨트랙트

#### (1) 지식 유효성 · 쓰레기 F_ID

| 논문 | 구현 |
|------|------|
| ID 존재 검사, 사실 연관 검증 | **생략** (FB13 그룹에 사전 매핑) |
| α=10 × 평균 제출 간격, 미확인 F_ID 수거 | `garbage_collect`, `alpha_ablation.py` |
| 의심 F_ID → 승인 피어 투표 | **없음** (즉시 recycle) |
| FB13 catalog 100 facts | `catalog_fact=True` → 가비지 제외 (논문 실험 사실과 정렬) |

#### (2) 기여자 신뢰도 · Follower

| 논문 | 구현 |
|------|------|
| 신뢰도 = 제출 트리플 품질 평균 | `_update_contributor_trust` (누적 평균) |
| Follower: Q = λ·Q_ST, λ=0.5 | `follower_quality`, 기본 λ=0.5 |
| Follower는 발행 시점에만 고정 | `Submission.is_follower` 불변 |
| Cheater (SOTA 복제) | `paper_sim` + `lambda_ablation` (event≥2000) |

#### (3) KQ 평가 · SOTA

| 논문 | 구현 |
|------|------|
| Algorithm 1, 식 (3)–(5) | `algorithm.py`, `tests/test_algorithm.py` |
| follower 제외 후 SOTA | `pick_sota` |
| SOTA 변경 시에만 비 follower 재평가 | 제출마다 `_run_kq_and_update_sota` (논문은 μ 비율로 일부만 — **단순화**) |

---

### 2.4 IV. 알고리즘 이론

| 항목 | 구현 |
|------|------|
| O(n²l) 복잡도 | 동일 구조, 기본 l=5 (`kq_iterations`) |
| Spammer 방어 논증 | 시뮬로 간접 검증만 (전용 spammer 실험 스크립트 없음) |

---

### 2.5 V. 구현 (Fabric)

| 논문 | 구현 |
|------|------|
| Hyperledger Fabric | **없음** |
| Procedure 1 TrPublish | `submit_triple` + 체인 `TR_PUBLISH` |
| Procedure 2 CheckVF | follower 판별 + `CHECK_VF` tx |
| Procedure 3 UpdateKQ | `evaluate_triple_qualities` + `UPDATE_KQ` / `SOTA_CHANGE` |
| 일괄 기여·트랜잭션 배칭 | 체인 `batch_size=25` (교육용만) |

---

### 2.6 VI. 실험

| 논문 실험 | 구현 |
|-----------|------|
| FB13, 100 (h,r) 그룹, pos/neg | `fb13_pairs_paper.tsv`, `load_fb13(pairs_only=True)` |
| 25 contributors, ~5000 submissions | `paper_sim.py` (데모는 1500으로 축소 가능) |
| SOTA accuracy vs MKPB/WMCA | **자체 지표만** (`sota_accuracy`, evolution metrics) |
| Spammer T_NUM, C.V. | **부분** (`alpha_ablation` 스팸 F_ID만) |
| FB2M 10M, 표 VI 시간 | **없음** |
| **확장: λ ablation** | `lambda_ablation.py` + 그래프 |
| **확장: α ablation** | `alpha_ablation.py` |
| **확장: SOTA evolution** | `sota_evolution.py`, churn, timeline |

**최근 smoke (5000, catalog fix):** confirmed 100, SOTA accuracy ~0.81, λ↑ 시 cheater trust↑.

---

## 3. 교육용 확장 (이번에 추가)

| 기능 | 경로 | 용도 |
|------|------|------|
| 미니 블록체인 | `src/chain.py`, `ledger.record_chain=True` | Procedure → tx → block → hash |
| HTML 대시보드 | `viz/dashboard.py`, `results/edu_dashboard.html` | 블록체인 + KG + SOTA 타임라인 |
| 데모 생성 | `python3 scripts/build_edu_demo.py` | 1500 제출 + 대시보드 |

---

## 4. 무엇을 주장할 수 있는가

**가능한 주장**

- 논문 **핵심 품질 평가 메커니즘(Alg.1)** 의 참조 구현 및 식 검증
- **Follower·λ·α·SOTA 진화** 에 대한 **확장 실험** (논문에 없는 ablation)
- FB13 스타일 데이터에서 **다중 기여자 시뮬** 결과

**불가/약한 주장**

- “논문과 동일한 Fabric 시스템을 재현했다”
- “표 V·VI 수치를 재현했다”
- “Hyperledger 보안·합의를 검증했다”

---

## 5. 권장 다음 단계 (선택)

1. `build_edu_demo.py`를 5000 제출로 실행해 논문 규모와 동일하게 데모
2. MKPB/WMCA 간이 baseline 추가 (VI Fig 재현 방향)
3. Fabric test-network + chaincode 포팅 (장기)

---

## 6. 실행 요약

```bash
cd extension_sim
python3 tests/test_algorithm.py
python3 tests/test_chain.py
python3 run_all.py
python3 scripts/build_edu_demo.py
# 브라우저에서 results/edu_dashboard.html 열기
```
