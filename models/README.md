# models (관제용 모델)

`notebooks/sayletskin/05_save_models.ipynb`가 만드는 배포용 모델 폴더. 모델 파일(`.joblib`)은 git에 올리지 않고 이 README만 올림. 관제 저장소(cal01-monitor)가 `scripts/import_models.py`로 복사해 감.

## 폴더와 이름

```
models/
  registry.json                      # 모델 ID → 경로, 구역, 라벨 버전, 입력 태그, 상태, 근거
  v6/
    zscore.json                      # 규칙형 (파일 없는 모델). 지난 값, min_periods 30, |Z| > 3, ddof 0
    final/                           # 입력 태그 final = common_roll10_zpast_opcommon_furnace_control
      Z4/
        rf-all14-<날짜>.joblib       # RandomForest, 14 LOT 전체. 관제 배포용
        rf-fold13-<날짜>.joblib      # RandomForest, LOT 1 ~ 13. 03의 마지막 시험과 같은 모델 (재현 확인용)
        iso-all14-<날짜>.joblib      # IsolationForest, 14 LOT 전체. 검토 후보 표시용
        features.json                # 입력 컬럼 순서와 계산 규칙
        config.json                  # 스위치, 파라미터, 학습 LOT, 라벨 규칙, 데이터 해시, 재현 확인 결과
        metrics.json                 # 03 시간순 걷기 결과
        fold13_expected.json         # fold13 모델의 LOT 133 예측 (관제 입력 계산 확인용)
      Z3/  Z5/  Z6/
```

- 모델 ID: `cal01-<라벨버전>-<입력태그>-<구역>-<모델>-<학습범위>-<날짜>` (예: `cal01-v6-final-Z4-rf-all14-20261024`)
- 모델 하나는 구역 하나만 예측함. 입력이 그 구역 센서와 공통 컬럼이기 때문
- 같은 조합을 다시 학습하면 날짜가 다른 새 ID가 생김. 이전 것은 관제 registry에서 `retired`로 바꿈

## 만드는 법

1. 03을 그 구역으로 먼저 실행해 `data/processed/model_results/`에 결과가 있어야 함 (metrics와 재현 확인에 씀)
2. 05의 1번 셀에서 `DATA_FILE`, `ZONE`을 정하고 실행. `USE_` 스위치는 03과 같은 값
3. 9번 셀의 재현 확인이 `True`인지 봄. `False`면 05의 입력 계산이 03과 어긋난 것
4. 구역마다 2 ~ 3을 반복 (지금은 Z3 ~ Z6)

## 관제로 옮기는 법

cal01-monitor 폴더에서:

```
python scripts/import_models.py --from ../pdm-project/models
```

- 파일을 `cal01-monitor/models/`로 복사하고 registry를 병합함. 이미 있는 ID는 건너뜀
- 관제는 registry에서 구역으로 모델을 찾고, 없는 구역은 Z-score만 씀

## 근거 단계 (registry의 `evidence`)

| 구역 | 모델 | 근거 |
| --- | --- | --- |
| Z3 ~ Z6 | RandomForest, IsolationForest | 팀 라벨 있음 (공통 움직임 해제 + 팀 판단) |
| 전 구역 | Z-score | 규칙형. 정답을 쓰지 않음 |
| 나머지 구역 | (없음) | 팀 라벨이 생기면 추가 (v7 모델 후보 라벨링 뒤) |
