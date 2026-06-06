# 논문 확장 실험 시뮬레이터

**논문:** Wang et al., *Decentralised Knowledge Graph Evolution via Blockchain*, IEEE TSC, 2024  
**DOI:** [10.1109/TSC.2023.3349164](https://doi.org/10.1109/TSC.2023.3349164)

---

## 1. 프로젝트가 하는 일

| 구분 | 내용 |
|------|------|
| **품질 평가** | Algorithm 1 (Eq. 3–5): 기여자 신뢰·트리플 일관성 → SOTA 선정 |
| **보안 메커니즘** | Follower `Q=λ·Q_SOTA`, 쓰레기 F_ID 수거 `α×평균 제출 간격` |
| **실험** | FB13 paper 모드 (100 facts, 5000 제출), λ/α/margin ablation |
| **교육 확장** | 미니 블록체인 + **3 peer 동기화** + SOTA KG HTML 대시보드 |

**블록체인이 개선하는 것:** KG 품질 알고리즘 자체가 아니라, **다중 기여자 제출·SOTA 변경 이력의 무결성·감사·노드 간 상태 일치**입니다.  
품질(SOTA accuracy 등)은 Alg.1 + follower + α가 담당합니다.

**공개 코드:** 본 논문 전용 GitHub/Fabric 체인코드 **없음** → 합의·Fabric 배포는 생략, 로직·시뮬·교육용 체인만 구현.

---

## 2. 빠른 시작

### WSL (권장)

```bash
# 1) 프로젝트 이동
cd ~/blockchain/extension_sim

# 2) venv (최초 1회)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt    # matplotlib (그래프용, 선택)

# 3) FB13 paper TSV (없을 때)
python scripts/mushroom_to_fb13_pairs.py \
  --freebase13-dir ../data/mushroom/Freebase13 \
  --out data/fb13_pairs_paper.tsv \
  --max-groups 100 --mode paper

# 4) 전체 실험
python run_all.py

# 5) 교육 데모 (3노드 + 대시보드)
python scripts/build_edu_demo.py
# → results/edu_dashboard.html 브라우저에서 열기
```

## 3. 디렉터리

```
extension_sim/
  src/
    algorithm.py      # Alg.1 (Eq. 3–5)
    ledger.py         # SOTA, follower, garbage, sota_update_margin
    chain.py          # 미니 해시 체인 (TrPublish 등)
    network.py        # 3-peer 네트워크
    peer.py           # 블록 replay, state digest
    paper_sim.py      # 논문 VI-B 시뮬 (5000 제출)
    fb13.py           # FB13 로더
    runner.py         # run_stream_fb13
    metrics.py        # SOTA 진화 지표
  experiments/        # ablation·smoke 스크립트
  scripts/
    build_edu_demo.py
    mushroom_to_fb13_pairs.py
  viz/dashboard.py    # HTML 대시보드 생성
  data/
    fb13_pairs_paper.tsv   # paper 실험용 (100 groups × 2 triple)
    fb13_pairs.tsv         # full 모드 (선택)
  results/            # JSON, PNG, edu_dashboard.html
  tests/              # algorithm, chain, peer sync
  docs/               # 상세 대조·가능성 문서
  run_all.py
```

---

## 4. 핵심 구현

### Algorithm 1 (Sec. IV)

```
q_i^l = q_i^{l-1} + (1/N) Σ W·Z
W = (1/l)(1-q_i)  [동의]  /  -(1/l)q_i  [불일치]
Z = (1/2)(q_e - q_i + 1) q_e
```

검증: `python tests/test_algorithm.py`

### 스마트 컨트랙트 로직 (Sec. III-C, 오프체인)

| 메커니즘 | 기본값 | 코드 |
|----------|--------|------|
| Follower | `Q = λ·Q_SOTA`, λ=0.5 | `ledger.follower_quality` |
| 쓰레기 F_ID | α=10 × 평균 제출 간격 | `ledger.garbage_collect` |
| SOTA 안정화 (확장) | `sota_update_margin=0.02` | margin 이상일 때만 SOTA 교체 |
| 확정 | `min_confirm=2` | 서로 다른 기여자 2명 |

### 3노드 원장 동기화

```
Peer 0 (Leader): submit → 블록 생성
Peer 1, 2:       블록 수신 → TR_PUBLISH replay → 동일 state digest
```

검증: `python tests/test_peer_sync.py`  
데모: `scripts/build_edu_demo.py` → 대시보드 **노드 동기화** 탭

---

## 5. 실험 목록 (`run_all.py`)

| 스크립트 | 목적 | 결과 파일 |
|----------|------|-----------|
| `tests/test_algorithm.py` | Eq. 3–5 단위 검증 | — |
| `tests/test_chain.py` | 해시 체인 무결성 | — |
| `tests/test_peer_sync.py` | 3 peer state 일치 | — |
| `experiments/fb13_smoke.py` | 논문 설정 smoke (5000, 3 seeds) | `fb13_smoke.json` |
| `experiments/lambda_ablation.py` | λ vs Cheater (FB13 5000, 3 seeds, 보조 지표) | `lambda_ablation.json/png` |
| `experiments/alpha_ablation.py` | α vs 스팸 F_ID (FB13 5000+주입, 3 seeds) | `alpha_ablation.json/png` |
| `experiments/sync_seed_robustness.py` | 3-peer 동기화 (시드 42/123/456) | `sync_seed_robustness.json` |
| `experiments/sota_evolution.py` | SOTA 변경·안정성 (3 seeds) | `sota_evolution.json/png` |
| `experiments/sota_margin_ablation.py` | 정확도–안정성 곡선 (3 seeds) | `sota_margin_ablation.json/png` |
| `experiments/fact_count_scenarios.py` | fact 카운트 분리 시나리오 | `fact_count_scenarios.json` |

### 논문 정렬 FB13 설정

- 데이터: `data/fb13_pairs_paper.tsv`
- 100 (head, relation) groups, 각 1 pos + 1 neg tail
- 25 contributors, 5000 submissions (데모는 1500)

---

## 6. 주요 결과 지표

| 지표 | 의미 |
|------|------|
| `sota_accuracy` | 확정 fact 중 SOTA가 정답 tail인 비율 |
| `num_confirmed_facts` | `min_confirm` 통과 fact 수 |
| `total_facts` | 원장 전체 fact 수 |
| `num_facts` | active(not recycled) fact 수 |
| `stable_fact_ratio` | 정답 SOTA 유지 + 변경 적은 fact 비율 |
| `churn_rate` | SOTA 변경 / 제출 수 |
| `avg_sota_changes_per_fact` | fact당 평균 SOTA 교체 횟수 |
| `sync_in_sync` | 3 peer state digest 일치 여부 (데모) |

**베이스라인 (5000 제출):** SOTA accuracy ≈ **0.80**, stable ≈ **0.80**, churn ≈ **0.008**

---

## 7. 교육용 대시보드

```bash
python scripts/build_edu_demo.py
```

`results/edu_dashboard.html` 탭:

| 탭 | 내용 |
|----|------|
| 노드 동기화 | Peer 0/1/2 state digest, OK/FAIL |
| 블록체인 | 블록·해시·TrPublish/CheckVF/UpdateKQ |
| SOTA KG | head→tail RDF 그래프, F_ID별 SOTA vs 후보 |
| SOTA 진화 | 라운드별 SOTA 교체 표 |

---

## 8. FB13 데이터 준비

### mushroom / Freebase13 (권장)

1. [gnodisnait/mushroom](https://github.com/gnodisnait/mushroom) 또는 Figshare:  
   https://ndownloader.figshare.com/files/13548377
2. 경로 예: `../data/mushroom/Freebase13/`  
   (`train_decoded_mushroom.txt.clean` 등)

### TSV 변환

```bash
# paper 모드 (실험용)
python scripts/mushroom_to_fb13_pairs.py \
  --freebase13-dir ../data/mushroom/Freebase13 \
  --out data/fb13_pairs_paper.tsv \
  --max-groups 100 --mode paper

# full 모드 (후보 많음, 선택)
python scripts/mushroom_to_fb13_pairs.py \
  --freebase13-dir ../data/mushroom/Freebase13 \
  --out data/fb13_pairs.tsv \
  --max-groups 100
```

TSV 형식 (탭, 헤더 없음): `head \t relation \t tail \t label` (`1`=정답, `0`=오답)

자세한 다운로드·인용: [`data/README_FB13.md`](data/README_FB13.md)

---

## 9. 논문 vs 구현 (요약)

| 영역 | 완성도 |
|------|--------|
| Alg.1 (Eq. 3–5) | **~95%** |
| follower·λ·α·SOTA 로직 | **~70–90%** |
| FB13 paper 실험 | **~60%** |
| 원장 KV (E_ID, 중복 인덱스) | **~25%** |
| Fabric / PBFT 합의 | **~15%** (미니 체인 + 3 peer replay) |
| FB2M 10M, 표 VI | **0%** |

**전체 프레임워크:** 약 **35–40%** (핵심 품질 메커니즘은 높음, 분산 인프라·대규모 실험은 낮음)

**주장 가능:** Alg.1 참조 구현, λ/α/SOTA 확장 실험, FB13 스타일 다중 기여자 시뮬, 3-node replay 동기화 데모  
**주장 불가:** Fabric 전체 재현, 논문 Table 수치 1:1 재현

상세 대조표: [`docs/PAPER_VS_IMPLEMENTATION.md`](docs/PAPER_VS_IMPLEMENTATION.md)

---

## 10. 블록체인·시각화 (교육용)

| 수준 | 현실성 |
|------|--------|
| A. 미니 원장 + 3 peer replay + HTML | **구현됨** |
| B. Fabric 축소 데모 | 부분 가능 (미구현) |
| C. 논문 10M 트리플 Fabric | 비현실 |

자세한 가능성 논의: [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md)

---

## 11. WSL 문제 해결

| 증상 | 조치 |
|------|------|
| `python3: command not found` | `sudo apt install python3 python3-venv` |
| matplotlib tk 오류 | `export MPLBACKEND=Agg` 또는 WSL에서 실행 |
| WSL 경로 느림 | `~/blockchain` 으로 복사 |
| paper TSV 없음 | §8 변환 스크립트 실행 |

전체 WSL 절차: [`SETUP_WSL.md`](SETUP_WSL.md)

---

## 12. 한계

- Hyperledger Fabric·PBFT·endorser **미구현**
- MKPB/WMCA baseline, FB2M 10M 실험 **없음**
- 단일 프로세스 시뮬 + 교육용 체인 (실 네트워크 P2P 아님)

---

## 13. 인용

- Wang et al., *Decentralised Knowledge Graph Evolution via Blockchain*, IEEE TSC, 2024.
- FB13 데이터: Dong et al., AAAI 2019 — [mushroom](https://github.com/gnodisnait/mushroom)
