# WSL 실행 가이드 (가상환경)

Windows에서 **WSL2 + Ubuntu** 기준입니다.

## 1. WSL 준비

```bash
# PowerShell(관리자) — 미설치 시
wsl --install -d Ubuntu
```

Ubuntu 터미널에서 프로젝트 경로로 이동 (Windows 드라이브는 `/mnt/c/...`):

```bash
cd /mnt/c/Users/dnrua/Desktop/blockchain/extension_sim
```

## 2. Python 및 venv

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt   # matplotlib (그래프, 선택)
```

이후 터미널을 열 때마다:

```bash
cd /mnt/c/Users/dnrua/Desktop/blockchain/extension_sim
source .venv/bin/activate
```

## 3. 구현 검증 (식 3–5)

```bash
python tests/test_algorithm.py
python tests/test_chain.py
python tests/test_peer_sync.py
```

`All algorithm tests passed.` 가 나오면 Alg.1 구현이 ExportBlock 수식과 일치합니다.

## 4. 확장 실험 실행

```bash
python run_all.py
```

결과: `results/*.json`, (matplotlib 설치 시) `results/*.png`

## 5. FB13 사용

1. `data/fb13_pairs_paper.tsv` 준비 (형식은 `data/README_FB13.md`)
2. 전체 실험: `python run_all.py` / 데모: `python scripts/build_edu_demo.py`

```bash
python -c "
from src.fb13 import load_fb13
from src.paper_sim import run_paper_ledger
L = run_paper_ledger(total_submissions=500)
print('SOTA accuracy:', L.sota_accuracy())
"
```

## 6. venv 비활성화

```bash
deactivate
```

## 문제 해결

| 증상 | 조치 |
|------|------|
| `python3: command not found` | `sudo apt install python3 python3-venv` |
| matplotlib 한글 깨짐 | 그래프는 영문 라벨 사용 (현재 스크립트) |
| WSL에서 Windows 경로 느림 | 가능하면 `~/blockchain` 으로 복사 후 작업 |
