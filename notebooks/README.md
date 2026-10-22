# 노트북

## 실행 순서

| 순서 | 노트북 | 하는 일 | 만드는 파일 |
| --- | --- | --- | --- |
| 1 | [namelesspark/01](namelesspark/01_data_alignment.ipynb) ~ [05](namelesspark/05_interval_review.ipynb) | 데이터 연결, 정비, LOT, 강종, 구간 탐색 | 그림 |
| 2 | [namelesspark/06](namelesspark/06_cal01_base_v1.ipynb) | 원기록 + 통계 후보 | `cal01_base_v1.csv` |
| 3 | [namelesspark/07](namelesspark/07_cal01_base_v2.ipynb) | v1 + 공통 움직임 해제 | `cal01_base_v2.csv` |
| 4 | [namelesspark/08](namelesspark/08_cal01_base_v3.ipynb) | v2 + 새로 찾은 공통 움직임 해제 | `cal01_base_v3.csv` |
| 5 | [namelesspark/09](namelesspark/09_cal01_base_v4.ipynb) | v2를 1분으로 묶음 | `cal01_base_v4.csv` |
| 6 | [namelesspark/10](namelesspark/10_cal01_base_v5.ipynb) | v3를 1분으로 묶음 | `cal01_base_v5.csv` |
| 7 | [namelesspark/11](namelesspark/11_cal01_base_v6.ipynb) | v3 + 팀 판단을 1분으로 묶음 | `cal01_base_v6.csv` |
| 8 | [sayletskin/03](sayletskin/03_model_f1.ipynb) | Dummy, Z-score, IsolationForest, RandomForest 비교 | `model_results/파일명_구역_*.csv` |
| 9 | [sayletskin/04](sayletskin/04_f1_summary.ipynb) | 버전별 F1 표, v5와 v6 비교 | 없음 (화면 표) |

- 06 ~ 11은 위 순서대로 한 번만 실행하면 됨 (07, 08, 11은 v1을, 09는 v2를, 10은 v3를 읽음. 11은 마지막에 v5와 비교하므로 10 다음에 실행)
- 03은 첫 셀의 `DATA_FILE`, `ZONE`만 바꿔서 여러 번 실행함

## v1 ~ v6 차이

| 버전 | 단위 | STAT_LABEL | DOMAIN_LABEL |
| --- | --- | --- | --- |
| v1 | 원기록 (1초) | 같은 LOT 기준 \|Z\| > 3 | 없음 |
| v2 | 원기록 (1초) | v1과 같음 | 공통 움직임 검토로 해제한 곳 0 |
| v3 | 원기록 (1초) | v1과 같음 | v2 + 새로 찾은 공통 움직임 해제 0 |
| v4 | 1분 | 1분 안에 후보가 하나라도 있으면 1 | v2를 1분으로 묶음 |
| v5 | 1분 | v4와 같음 | v3를 1분으로 묶음 |
| v6 | 1분 | v4와 같음 | v3 + 팀 판단(1, 0)을 1분으로 묶음 |

- `LABEL`은 CSV에 없음. 모델 노트북에서 `DOMAIN_LABEL`이 있으면 그 값, 없으면 `STAT_LABEL`로 만듦
- 팀 검토 내용은 `data/labels/domain_decisions.csv` 한 곳에 모음 (LOT, 센서, 시작, 끝, 0 또는 1, 이유)

## 공통 경로 양식

모든 노트북의 첫 코드 셀에 그대로 붙임. 노트북마다 `DATA_FILE` 한 줄만 바꿈.

```python
import os
import pandas as pd

# 저장소 루트 찾기: notebooks 폴더가 안 보이면 한 칸 위로 (최대 두 번)
ROOT = os.getcwd()
for step in range(2):
    if not os.path.isdir(os.path.join(ROOT, "notebooks")):
        ROOT = os.path.dirname(ROOT)

# 폴더
DATA_DIR = os.path.join(ROOT, "data")                    # 원본 CSV 8개
if os.path.isfile(os.path.join(DATA_DIR, "raw", "T-CR1-CAL01_온도.csv")):
    DATA_DIR = os.path.join(DATA_DIR, "raw")             # data/raw에 두었으면 그 폴더를 씀
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")  # 만든 CSV (cal01_base_v1 ~ v6)
LABEL_DIR = os.path.join(ROOT, "data", "labels")         # 팀 검토 표 (domain_decisions.csv)
FIG_DIR = os.path.join(ROOT, "figures")                  # 그림
ENC = "utf-8-sig"

# 원본 CSV
TEMP_CSV = os.path.join(DATA_DIR, "T-CR1-CAL01_온도.csv")
EVENT_CSV = os.path.join(DATA_DIR, "G-02_조업이벤트.csv")
REPAIR_CSV = os.path.join(DATA_DIR, "G-01_정기수리캘린더.csv")
EQP_CSV = os.path.join(DATA_DIR, "G-01_설비마스터.csv")
PART_CSV = os.path.join(DATA_DIR, "G-01_부품마스터.csv")
MAINT_CSV = os.path.join(DATA_DIR, "G-02_정비이력.csv")
PARTCHG_CSV = os.path.join(DATA_DIR, "G-02_부품교체이력.csv")
WELD_CSV = os.path.join(DATA_DIR, "T-CR1-WLD01_용접.csv")

# 읽을 가공 CSV (이름만 바꾸면 됨)
DATA_FILE = "cal01_base_v1.csv"
BASE_CSV = os.path.join(PROCESSED_DIR, DATA_FILE)
```

## 폴더 규칙

| 폴더 | 내용 |
| --- | --- |
| `namelesspark/` | 탐색(01 ~ 05)과 가공 CSV 만들기(06 ~ 10) |
| `sayletskin/` | 모델 비교(03, 04) |
| 그 밖 개인 폴더 | 각자의 탐색 노트북 |

- 결과 CSV는 실행할 때마다 같은 이름으로 덮어씀. 시각이 붙은 결과 폴더는 만들지 않음
- 커밋 전에 노트북 출력을 지움 (`nbstripout`을 등록하면 `git add` 때 자동으로 지워짐)
- 노트북 출력에는 원본 데이터가 그대로 남을 수 있으므로 공개 저장소에는 출력 없이 올림
