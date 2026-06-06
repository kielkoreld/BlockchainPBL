# FB13 데이터 확보 (mushroom / Freebase13)

논문 Wang et al. (IEEE TSC 2024)의 **FB13**은 triple classification용 Freebase 서브셋으로,  
동일 **(head, relation)** 에 서로 다른 **tail** 후보(정답/오답) 쌍이 약 **23,733**개입니다.

공개 배포: [gnodisnait/mushroom](https://github.com/gnodisnait/mushroom) (AAAI-19, Freebase13)

---

## 방법 A — mushroom 공식 다운로드 (권장)

### 1) 저장소 클론 (WSL)

```bash
cd ~
git clone https://github.com/gnodisnait/mushroom.git
cd mushroom
```

### 2) 데이터 경로 설정

`mushroom/config.py` 에서 `dataPath` 를 **절대 경로**로 수정:

```python
dataPath = "/home/YOUR_USER/data/mushroom"
```

### 3) Figshare에서 Freebase13 자동 다운로드

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_ubuntu.txt   # urllib, zip 등 — 용량 큼, 시간 소요

python mushroom.py --func download
```

성공 시 다음 폴더가 생깁니다:

```
$dataPath/Freebase13/
  train_decoded_mushroom.txt
  valid_decoded_mushroom.txt
  test_decoded_mushroom.txt
  entity2vec.*.50
  mushroom_structure.txt
  ...
```

Figshare 직접 URL ([config.py](https://github.com/gnodisnait/mushroom/blob/master/mushroom/config.py)):

- **Freebase13:** https://ndownloader.figshare.com/files/13548377

---

## 방법 B — zip만 받기 (mushroom 코드 없이)

```bash
mkdir -p ~/data/mushroom/Freebase13
cd ~/data/mushroom
wget -O freebase13.zip "https://ndownloader.figshare.com/files/13548377"
unzip -o freebase13.zip -d Freebase13
# zip 루트에 txt가 있으면 Freebase13/ 로 옮기기
ls Freebase13/
```

`train_decoded_mushroom.txt` 등이 보이면 OK.

---

## extension_sim 형식으로 변환

```bash
cd /mnt/c/Users/dnrua/Desktop/blockchain/extension_sim
source .venv/bin/activate   # 또는 blockchain venv

# 데이터가 blockchain/data/mushroom/ 에 있으면 (extension_sim 밖):
python scripts/mushroom_to_fb13_pairs.py \
  --freebase13-dir ../data/mushroom/Freebase13 \
  --out data/fb13_pairs.tsv \
  --max-groups 100

# 또는 절대 경로
python scripts/mushroom_to_fb13_pairs.py \
  --freebase13-dir /mnt/c/Users/dnrua/Desktop/blockchain/data/mushroom/Freebase13 \
  --out data/fb13_pairs.tsv \
  --max-groups 100
```

`.clean` 접미사 파일(`train_decoded_mushroom.txt.clean` 등)도 자동 인식합니다.

출력 `fb13_pairs.tsv` (탭 구분, 헤더 없음):

```
head	relation	tail	label
```

- `label`: `1` = 정답 tail, `0` = 오답 tail

로더: `load_fb13()` (`src/fb13.py`)

---

## 파일 형식 (mushroom)

| 파일 | 한 줄 형식 | 의미 |
|------|------------|------|
| `train_decoded_mushroom.txt` | `H T R` | 정답 트리플 |
| `valid_decoded_mushroom.txt` | `H T R` | 정답 트리플 |
| `test_decoded_mushroom.txt` | `H T R LABEL` | `True`/`1` 정답, `False`/`-1` 오답 |

엔티티 ID 예: `/m/027rn`, 관계: `/location/location/contains`

---

## 1~2주 일정에 맞는 규모

| 선택 | 작업량 | 용도 |
|------|--------|------|
| **100 groups** (`--max-groups 100`) | 다운로드 + 변환 **반나절** | λ/α/SOTA 확장 (논문 §VI-B와 동일 규모) |
| **전체 ~23k groups** | 변환·시뮬 **수 시간~1일** | 대규모 재현 (이번 확장 필수 아님) |

---

## 검증

```bash
python -c "
from src.fb13 import load_fb13
g = load_fb13(max_groups=100)
print('groups', len(g))
print('example', g[0].ground_truth, len(g[0].candidates))
"
```

---

## 인용

mushroom / Freebase13 사용 시:

- Tiansi Dong et al., *Triple Classification Using Regions and Fine-Grained Entity Typing*, AAAI 2019.  
  [https://github.com/gnodisnait/mushroom](https://github.com/gnodisnait/mushroom)

KG 논문:

- Wang et al., *Decentralised Knowledge Graph Evolution via Blockchain*, IEEE TSC 2024.
