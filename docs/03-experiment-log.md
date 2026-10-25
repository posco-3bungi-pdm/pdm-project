# 실험 기록

2026-10-26에 `main`의 `b5e67e4`와 로컬 결과 파일을 대조해 정리함.
이번 문서 정리에서 모델을 다시 학습하거나 CSV를 바꾸지는 않았음.
아래 점수는 실제 고장 정답이 아닌 분석 라벨과의 일치도임.

## 1. 라벨을 바꾼 이유

| 버전 | 확인하려던 것 | 바꾼 내용 | 관련 PR |
| --- | --- | --- | --- |
| v1 | 센서와 조업 기록을 같은 행에서 볼 수 있는가 | 원래 관측 간격의 공통 데이터 구성 | [#112](https://github.com/posco-3bungi-pdm/pdm-project/pull/112)에서 현재 생성 코드로 정리 |
| v2 | 3σ 후보에 반복되는 조업 움직임이 섞이는가 | 각 LOT의 3σ 후보와 첫 공통 움직임 검토 반영 | [#96](https://github.com/posco-3bungi-pdm/pdm-project/pull/96), [#112](https://github.com/posco-3bungi-pdm/pdm-project/pull/112) |
| v3 | 어느 구역의 후보인지 구분할 수 있는가 | 구역별 라벨과 추가 공통 움직임 검토 반영 | [#102](https://github.com/posco-3bungi-pdm/pdm-project/pull/102), [#109](https://github.com/posco-3bungi-pdm/pdm-project/pull/109) |
| v4 | 1분으로 줄여도 짧은 후보를 남길 수 있는가 | 분별 평균, 최소, 최대, 표준편차, 관측 수 저장 | [#103](https://github.com/posco-3bungi-pdm/pdm-project/pull/103) |
| v5 | 다른 구역과 앞쪽에도 공통 움직임이 있는가 | 검토한 센서와 시간만 후보에서 해제 | [#107](https://github.com/posco-3bungi-pdm/pdm-project/pull/107) |
| v6 | 통계 후보에 팀 판단을 반영하면 어떻게 달라지는가 | T 판단과 S 전 구역 검토 반영 | [#114](https://github.com/posco-3bungi-pdm/pdm-project/pull/114), [#121](https://github.com/posco-3bungi-pdm/pdm-project/pull/121) |
| v7 | 출력만 큰 변화와 작은 온도 변화를 계속 1로 둘 것인가 | M 검토, T32, 출력 단독 초과와 온도 편차 0.5℃ 미만 해제 규칙 추가 | [#123](https://github.com/posco-3bungi-pdm/pdm-project/pull/123) |

현재 v1부터 v7은 [06번부터 13번 노트북](../notebooks/README.md)에서 생성함.
과거 PR의 중간 결과와 현재 생성 코드의 결과는 구분해서 읽어야 함.

| 1분 라벨 | 구역별 라벨 1 합계 | 그중 Z4 |
| --- | ---: | ---: |
| 통계 후보만 | 2,922 | 527 |
| v4 | 2,595 | 527 |
| v5 | 2,128 | 464 |
| v6 | 1,912 | 493 |
| v7 | 435 | 249 |

분모는 제외 구간을 뺀 5,617분이고, 합계는 여러 구역의 1을 더한 수임.
고유 시각 수나 고장 건수가 아님.
같은 5,938행을 유지하면서 라벨과 판단 근거를 바꿨음.

`STAT_LABEL`은 검토 전 3σ 후보, `DOMAIN_LABEL`은 팀 검토 값임.
모델의 기본 `LABEL_RULE="v6"`는 팀 판단이 있으면 그 값, 없으면 통계 후보를 사용함.
이 옵션 이름은 v7 CSV에도 적용되는 규칙 이름임.
`team_only`는 팀이 보지 않은 통계 후보를 비우는 별도 실험이고, 아래 최종 점수와 섞지 않음.

검토 표 전체 395행은 0이 346행, 1이 22행, 빈칸이 27행임.
적용 버전인 v2, v3, v6, v7은 361행이고, 제안 또는 보류 버전 34행은 반영하지 않음.
v7의 규칙 2개와 일부 판단은 팀 확인이 남아 있음.
라벨을 줄여 점수가 달라진 것을 모델 자체의 성능 향상으로 설명하지 않음.

## 2. 1분 모델 비교

- 코드: [sayletskin/03_model_f1.ipynb](../notebooks/sayletskin/03_model_f1.ipynb)
- 입력: `cal01_base_v7.csv`, 기본 라벨 규칙
- 학습: 앞 4개 LOT으로 시작해 다음 LOT을 시험하고, 그다음에는 과거 LOT을 추가함
- 시험: 240044부터 240133까지 10개 LOT, Z4는 3,633분
- 입력 묶음: 기본 통계, 공통 움직임, 직전 10분 통계, 과거 Z, 출력 공통 움직임, 여러 구역의 동시 초과, TC와 OP의 같은 방향 비율
- Z-score: 현재 분을 뺀 같은 LOT 과거 기록, 최소 30분, 3σ
- RF: 나무 100개, 깊이 10, `class_weight="balanced"`, 확률 0.5, `random_state=42`
- IF: 나무 100개, Train 라벨 1 비율로 contamination 설정, `random_state=42`

IF는 센서값으로 학습하지만 후보율 설정에는 Train 라벨 비율을 사용했음.
라벨을 전혀 참고하지 않은 설정이라고 설명하지 않음.
분 라벨은 LOT 전체 통계를 쓰고 예측 입력은 과거 통계를 쓰므로 두 기준의 시점이 다름.

| v7 Z4 | TP | FP | FN | TN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Dummy 0 | 0 | 0 | 165 | 3,468 | 0 | 0 | 0 |
| Z-score | 107 | 86 | 58 | 3,382 | 0.5544 | 0.6485 | 0.5978 |
| IsolationForest | 96 | 132 | 69 | 3,336 | 0.4211 | 0.5818 | 0.4885 |
| RandomForest | 96 | 67 | 69 | 3,401 | 0.5890 | 0.5818 | 0.5854 |

RF는 Z-score보다 FP가 적었지만 FN은 많았음.
하나의 모델이 모든 지표에서 앞선 결과는 아님.
Dummy는 센서를 보지 않는 비교 수준이며 주 기준선은 Z-score임.

근거 파일: `data/processed/model_results/cal01_base_v7_Z4_common_roll10_zpast_opcommon_furnace_control_summary.csv`.
LOT별 값은 같은 이름의 `by_lot.csv`, 각 분의 판정은 `predictions.csv`에 있음.
원본과 결과 CSV는 로컬에 두고 Git에 올리지 않음.
설정과 표를 확인할 곳은 [모델 비교](../notebooks/sayletskin/03_model_f1.ipynb), [F1 요약](../notebooks/sayletskin/04_f1_summary.ipynb)임.

## 3. 추가 입력과 모델 설정

| 질문 | 확인한 결과 | 남긴 판단 |
| --- | --- | --- |
| 강종 계열과 출력 부담을 더하면 좋아지는가 | 계열 원핫, 계열 편차, 출력 합, 구역 간 온도차 등을 더해도 여러 구역이 함께 좋아지지 않았음 | 기본 옵션은 끔 |
| RF를 깊게 만들고 시차 입력을 더하면 좋아지는가 | Z4 F1 0.653, 일부 다른 구역은 하락 | 추가 확인이 필요한 실험으로 남김 |
| 앞 8개 LOT에서 설정을 고르면 뒤 6개에서도 좋아지는가 | 뒤 6개 F1 0.527, 같은 구간의 기본 설정은 0.604 | 탐색 설정을 최종값으로 채택하지 않음 |

관련 변경: [#121](https://github.com/posco-3bungi-pdm/pdm-project/pull/121), [#123](https://github.com/posco-3bungi-pdm/pdm-project/pull/123).
특정 LOT을 여러 번 본 탐색 결과이므로, 아직 보지 않은 미래 데이터의 성능으로 주장하지 않음.

## 4. 2단계 후보 모델

1분 경보가 이어진 구간을 하나의 후보로 묶고, 팀 판단이 있는 후보만으로 RF를 학습했음.
코드는 [namelesspark/14_candidate_rf.ipynb](../notebooks/namelesspark/14_candidate_rf.ipynb)임.
관련 변경은 [#127](https://github.com/posco-3bungi-pdm/pdm-project/pull/127), [#130](https://github.com/posco-3bungi-pdm/pdm-project/pull/130)임.

- Z-score 후보 532개 중 팀 판단이 있는 후보는 214개, 그중 1은 12개
- RF: 나무 300개, 깊이 제한 없음, 잎 최소 2개, `class_weight="balanced"`, `random_state=42`
- 후보 확률 0.5 이상을 1로 판정

| 평가 | 팀 1 포착 | 팀 0 중 제외 | Precision | F1 |
| --- | ---: | ---: | ---: | ---: |
| 모든 후보를 1로 | 12/12 | 0/202 | 0.056 | 0.106 |
| CP 과거 Z가 3 초과인 규칙 | 11/12 | 184/202 | 0.379 | 0.537 |
| RF, LOT 하나를 빼고 학습 | 8/12 | 197/202 | 0.615 | 0.640 |
| RF, 과거 LOT만 학습 | 7/11 | 145/148 | 0.700 | 0.667 |
| RF, 앞 7 LOT 학습 후 뒤 7 LOT 평가 | 7/8 | 115/116 | 0.875 | 0.875 |

후보 하나를 맞혔는지 평가한 수치임.
위의 1분 모델 F1과 직접 순위를 매기지 않음.
LOT 하나를 빼는 평가에는 시험 LOT보다 뒤의 LOT도 학습에 들어갈 수 있음.
시간순 평가와 같은 방식으로 설명하지 않음.
후보 뒤 10분의 온도 반응도 사용하므로, 후보 발생 즉시 판단하는 모델은 아님.
팀 1 후보가 12건뿐이라 새 LOT으로 재확인이 필요함.

판단이 없는 318개는 점수 순으로 정렬했고, 0.5 이상인 12개를 다음 검토 대상으로 남겼음.
저장 파일은 `data/processed/candidates_zscore.csv`, `candidate_rf_ranked.csv`임.
예측 점수를 새 도메인 라벨 1로 자동 반영하지 않음.

## 5. 저장과 재현

- [05_save_models.ipynb](../notebooks/sayletskin/05_save_models.ipynb)는 관제용 모델과 설정을 저장함
- 모델 파일과 CSV는 로컬에 두고, 저장 규칙은 [models/README.md](../models/README.md)에 적음
- 그림과 오류 해석은 [결과보고서 6장](../reports/결과보고서.md#6-평가와-오류-분석)에 있음
- 시계열 근거는 [보고서 목록](../reports/README.md)의 시계열 분석 PDF에서 확인함

입력 CSV와 검토 표를 준비한 뒤 각 노트북을 위에서부터 실행함.
같은 난수 시드를 사용해도 CSV, 라벨 규칙, 입력 옵션이 다르면 결과가 달라짐.
모델 지표 파일이 있으면 다음 명령으로 혼동행렬과 지표 계산을 대조할 수 있음.

```bash
python src/check_delivery.py --results-dir data/processed/model_results
```

이 검사는 저장된 지표 계산을 확인함.
재학습이나 실제 고장 탐지 성능 검증을 대신하지 않음.
