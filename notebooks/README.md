# 노트북

## namelesspark 소둔로 분석

| 순서 | 내용 |
| --- | --- |
| [01](namelesspark/01_data_alignment.ipynb) | 설비, LOT, 강종과 측정시각 연결 |
| [02](namelesspark/02_maintenance_parts.ipynb) | 정비와 부품교체 확인 |
| [03](namelesspark/03_lot_comparison.ipynb) | LOT별 센서 비교 |
| [04](namelesspark/04_grade_comparison.ipynb) | 같은 강종의 LOT 비교 |
| [05](namelesspark/05_interval_review.ipynb) | 제외 구간과 이상 후보의 근거 확인 |

각 노트북은 `data/`의 원본 CSV를 직접 읽어 독립 실행함. 그림은 `figures/namelesspark/`의 같은 번호 폴더에 저장함. 공통 CSV 생성과 모델 실험은 후속 PR로 분리함.

이전 탐색은 [정리 전 노트북](https://github.com/posco-3bungi-pdm/pdm-project/tree/dcc7f5e4c65a9de9a2af7622cddcfbe3bd42bfef/notebooks)에 보존함.

## 공통 안내

`01_eda.ipynb`, `02_timeseries.ipynb`, `03_model.ipynb`, `04_eval.ipynb` 순서를 권장합니다. 실제 분석이 시작될 때 생성합니다. 같은 파일은 한 명씩 맡고, 공통 로직은 `src/`로 옮깁니다. 커밋 전에 출력을 지우고 결과 그림은 검토 후 `figures/`에 저장합니다. `nbstripout` 필터를 등록해 두면 `git add` 시점에 출력이 자동으로 제거됩니다(등록 방법은 [README](../README.md) 시작하기 참고). 출력에는 `df.head()` 같은 원본 데이터 행이 그대로 남기 때문에 공개 저장소에서는 반드시 지우고 커밋합니다.
