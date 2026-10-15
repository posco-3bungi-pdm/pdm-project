# 소둔로 데이터 분석 흐름

기존에 확인했던 걸 처음부터 다시 분석하지 않게 역할을 나눴음.
설비·LOT 연결 → 정비·부품 → LOT별 관찰 → 같은 강종 비교 → 구간 판정 → 파생컬럼 → 데이터프레임 순서로 보면 됨.

| 순서 | 노트북 | 여기서 확인할 것 | 다음에 넘기는 것 |
| --- | --- | --- | --- |
| 01 | [설비·LOT·강종 연결 기준](01_data_alignment.ipynb) | 어느 설비의 데이터인지, 실제 관측 구간과 강종이 어떻게 연결되는지 | 설비 태그, 실제 LOT 경계, 강종 매핑 |
| 02 | [정비 → 부품 연결](02_maintenance_parts.ipynb) | BM·TBM·CBM에서 어떤 부품이 교체됐는지, 교체 없는 정비는 몇 건인지 | 정비 1건당 1행인 표와 부품별 상세 표 |
| 03 | [LOT별 온도·출력 비교](03_lot_comparison.ipynb) | 한 LOT 안에서 TC·OP·CP가 어떻게 움직이는지 | LOT별 관찰과 비교 그림 |
| 04 | [같은 강종의 LOT 비교](04_grade_comparison.ipynb) | 같은 강종에서도 반복되는 움직임인지 | 강종 내 공통점과 다른 사례 |
| 05 | [제외 구간과 라벨 근거 검토](05_interval_review.ipynb) | 어느 구간을 제외할지, 이상이라고 판단할 근거가 있는지 | 원본 행 단위 제외·후보·판정 검토표 |
| 06 | [과거 센서값으로 파생컬럼 만들기](06_feature_derivation.ipynb) | 관찰한 흐름을 어떤 숫자로 표현할지 | 사용자 제외 조건을 반영한 1분 단위 과거 파생컬럼 후보 |
| 07 | [라벨·파생컬럼 데이터프레임 생성](07_labeled_dataframe.ipynb) | 원본 관측 행에 과거 특징과 임시 0·1을 어떻게 붙일지 | 전체 원본 행을 보존한 공통 기준표 |

## GitHub 작업과 연결

| 주제 | 현재 담당 노트북 | 기존 이슈·PR | 이번에 이어지는 작업 |
| --- | --- | --- | --- |
| 설비·LOT·강종 연결 | 01 | [#10](https://github.com/posco-3bungi-pdm/pdm-project/issues/10) / PR #22, [#30](https://github.com/posco-3bungi-pdm/pdm-project/issues/30) / PR #37, [#45](https://github.com/posco-3bungi-pdm/pdm-project/issues/45) / PR #51 | 흩어진 연결 검증을 01에 모음. #45의 8개 자료 커버리지 전체를 완료했다는 뜻은 아님 |
| 정비·부품·DOWN_MIN | 02 | [#41](https://github.com/posco-3bungi-pdm/pdm-project/issues/41) / PR #63의 종합 EDA | 센서 반복 분석을 빼고 정비 1건당 1행·부품 상세·정지 분량 의미를 관리함 |
| LOT·강종별 센서 비교 | 03·04 | [#71](https://github.com/posco-3bungi-pdm/pdm-project/issues/71) / PR #72 | 기존 02·03을 현재 03·04로 옮김. SPHC TC-Z7·Z8 검토를 04에 추가함 |
| 제외 구간·센서 후보·정비 근거 | 05 | [#74](https://github.com/posco-3bungi-pdm/pdm-project/issues/74), 이전 #45 상세 검토 참고 | 네 제외 구간과 전체 계측 후보를 근거표로 연결함 |
| 과거 파생컬럼 | 06 | #41 → #71 / PR #72 | 기존 01을 현재 06으로 옮기고 사용자 제외 조건을 반영함 |
| 임시 0·1 기준표·입력 정의 | 07 | #74 | 05 근거와 06 특징을 합쳐 공통 기준표를 생성함 |
| 분할·9:1·모델 비교 | 아직 없음 | #74 | 시간·LOT 분할 후 Z-score·IF·RF 비교. 기존 회귀 실험과 구분함 |

읽는 순서는 01 → 02 → 03 → 04 → 05 → 06 → 07임. 실행할 때 이전 노트북의 메모리를 이어받는 것은 아님. 01~06은 원본과 공통 함수로 독립 실행하며, 07만 05·06의 저장 결과를 읽음.

PR #63은 이미 #72로 대체되어 닫힌 과거안임. 이번 #74 브랜치에는 #72의 03·04·06에 해당하는 작업도 포함됐으므로 새 PR에서 함께 검토하고 중복 병합하지 않음. #71의 시각화·파생변수와 #74의 모델링 완료 기준은 따로 봐야 함.

## 역할을 나눈 기준

- 설비·LOT·강종 정의는 01에서 확인함. 예전처럼 다음 LOT 시작까지 빈 시간을 이전 LOT에 포함하지 않음.
- 정비·부품 분석과 대기시간 박스플롯은 02에서만 관리함. LOT별 그래프와 강종별 그래프는 03·04에서 관리함.
- `DOWN_MIN`과 작업시간 비교는 02, SPHC 마지막 LOT의 TC-Z7·Z8 수준 차이는 04에서만 계산함. 05는 해당 결과를 검토 근거로 연결함.
- 원본 읽기, LOT·강종 연결, 정비·부품 연결, 사용자 지정 제외 경계는 [공통 코드](../../src/namelesspark_pipeline.py)에서 관리함.
- 02의 전체 정비 표는 교체 없는 정비도 left join으로 남김. 같은 WO에서 부품 2종을 바꿔도 정비 행을 복제하지 않음. 현재 정비 44건과 부품 상세 9행은 서로 다른 단위임.
- 03·04는 제외할 운전 구간까지 비교할 수 있게 원본을 관찰함. 05에서 제외를 표시하고, 06은 같은 공통 제외 조건을 적용한 뒤 파생컬럼을 계산함.
- 센서 후보와 정비가 시간상 가깝다는 것만으로 원인을 확정하지 않겠음. 사후 정비·교체 결과는 라벨 검토 근거이고, 과거 시점의 모델 입력으로 바로 쓰는 값은 아님.

## 첫 실험 기준표 v1

`data/processed/cal01_base_v1.csv` 하나를 기준으로 비교하면 됨. LOT·측정시각 순서이며 원본 한 행이 기준표 한 행임. 조인이나 샘플링으로 행을 늘리지 않았음.

| 구분 | 행 수 | 의미 |
| --- | ---: | --- |
| 전체 | 345,390 | 원본 관측 전부 보존 |
| 임시 0 | 325,253 | 이번 센서+정비 규칙 미검출. 정상 확정은 아님 |
| 임시 1 | 1,483 | 강한 지속 신호와 적격 정비의 시간 연관을 함께 만족 |
| 사용자 제외 | 18,654 | EXCLUDED=True, LABEL 비움. 학습에서 제외 |
| 모델 입력 가능 | 318,500 | 제외되지 않았고 입력 67개가 모두 있는 행. 0=317,017 / 1=1,483 |

나머지 8,236개 비제외 행은 센서 결측 또는 과거 이력 부족 때문에 `MODEL_ELIGIBLE=False`임. 원본과 라벨은 기준표에 남겨둠. 1은 모델 입력 가능 행 기준 약 0.47%이며 원하는 비율에 맞춘 숫자가 아님.

### 임시 0·1을 붙인 조건

사용자가 전체 센서·CSV 근거를 조합한 임시 라벨로 첫 실험을 진행하기로 선택했음. 현장 확정 정답과 구분해서 사용함.

- 의미가 확인된 21계측을 검토함. CP-Z4M은 원본에 보존하지만 의미 미확인 보조계측이라 판정·X에서 제외함.
- LOT·센서별 과거 5분 기준선에서 벗어난 실제 1초 간격 10초 이상 후보 중 최대 이탈이 후보 문턱의 2배 이상인 구간을 사용함. 모든 행이 2배를 넘는다는 뜻은 아님.
- 같은 CAL01의 BM·CBM 중 ELE·MAL·WER 기록, 또는 손상 부품교체가 있는 TBM과 연결함. 원인미상·확인중·이상없음 등 기록은 양성 근거에서 뺌. 감지 전 24시간 또는 작업 종료 후 24시간 안의 실제 후보 행만 사용함.
- CP는 같은 LOT 중앙값에서 12×MAD 기반 표준편차를 초과한 행만 남겨 정상 수준 복귀를 1로 붙이지 않게 함.
- 현재 v1은 모든 OP 후보를 제어반응으로 분류해 양성에서 보류함. 같은 존 TC와 10초 이상 겹치는 조건도 코드에 있지만 앞의 보류 조건 때문에 OP 채택으로 이어지지 않음. OP 동반 신호를 허용하려던 설명과의 차이는 #74에서 검토할 항목임.
- TC-Z3 및 모든 OP의 제어반응, 반복주기 채널, LOT 경계, 작업 중, 수리일정과 그 전후 24시간은 양성으로 채택하지 않음. 사용자 지정 제외 이외의 미채택 행은 이번 실험에서 0임.
- 다른 LOT보다 TC-Z7·Z8 수준이 높다는 이유로 LOT 전체를 1로 만들지 않음. 설정값이 없어 수준 차이는 검토 항목으로 남음.

문턱·24시간·수리 전후 범위는 실험 가정임. 강종별 공정 허용치가 확정된 것은 아님. 같은 강종 안에서도 LOT별 국소 변화를 사용하지만 설정값·운전단계 차이를 전부 해소하지 못함. 적격 정비와 가깝다는 사실만으로 가스 누출이나 특정 존 고장을 확정하지 않음.

현재 1은 LOT 240069=895행, 240117=224행, 240121=364행임. 센서 기여는 CP-Z4=1,138행, TC-Z6=345행임. 전체 센서를 검토한 결과이지 CP만 판정한 결과가 아님. 3개 LOT에 모여 있어 다른 LOT에서 성능이 유지되는지는 별도 검증이 필요함.

### 기준표 컬럼

| 컬럼 | 용도 |
| --- | --- |
| ROW_ID, LOT_NO, MEAS_DT, GRADE | 원본 행·LOT·시간·강종 식별. 분할과 결과 확인용 |
| 원본 22계측 | 원본 값 보존. X에서는 CP-Z4M 제외 |
| 과거 특징 38개, LOT_ELAPSED_MIN, GRADE_* | 현재 분 시작 전에 완성된 과거 특징과 강종 인코딩 |
| EXCLUDED, EXCLUSION_REASON | 사용자 제외 표시 |
| FEATURES_COMPLETE, MODEL_ELIGIBLE | 결측·이력 부족과 실제 입력 가능 여부 |
| LABEL, LABEL_STATUS, LABEL_VERSION | 임시 목표값·판정 상태·규칙 버전 |
| LABEL_REASON, RULE, EVIDENCE_* | 근거 WO·센서·정비유형·DOWN_MIN·부품교체·판정 이유. X에서 제외 |
| LOT_CONTEXT_ID, SENSOR_CANDIDATE_IDS, 문맥 플래그 | 05의 상세 근거 연결. X에서 제외 |

`EVIDENCE_DOWN_MIN` 등은 `WO:값` 형식이며 라벨 1의 근거 정비를 설명함. 빈칸은 정비가 전혀 없다는 뜻이 아님. 0인 행을 포함한 전후 사건은 `review/v1/05_domain_context.csv`에서 연결 ID로 확인함. `DOWN_MIN`은 정비 기록의 정지 분량이며 그 행 시각에 실제로 멈췄다는 뜻이 아님. `EVIDENCE_INPUT_ALLOWED=False`는 근거 컬럼을 X에 넣지 말라는 표시임.

### 분류와 회귀

원본 기준표는 공유하고 정답 y의 정의만 분리함. 동일한 큰 CSV를 분류·회귀 폴더에 복제하지 않음.

- `classification/v1/dataset.json`: 입력 67개와 LABEL 정의. Z-score·IsolationForest·RandomForestClassifier가 같은 평가 행을 비교할 때 사용함. Z-score·IF의 fit에 LABEL을 넣지 않음.
- `regression/v1/dataset.json`: 같은 기준표를 참조함. 목표 센서·몇 초 뒤를 예측할지 아직 미정임. `regression_inputs()`는 정한 뒤 같은 LOT의 정확한 미래 시각을 연결하고 사용자 제외·분할 경계를 넘는 정답을 뺌.
- LABEL·라벨 근거·사후 정비·부품교체·후보 플래그는 X가 아님. 문자열이어도 인코딩하면 입력될 수 있으니 컬럼 허용목록으로 차단함.

```python
import json
import pandas as pd
from namelesspark_datasets import classification_inputs, sha256

contract = json.loads((ROOT / 'data/processed/classification/v1/dataset.json').read_text(encoding='utf-8'))
path = ROOT / 'data/processed/cal01_base_v1.csv'
assert sha256(path) == contract['master_sha256']
master = pd.read_csv(path, encoding='utf-8-sig', parse_dates=['MEAS_DT'], dtype={'LABEL': 'Int8'})
X, y, row_keys = classification_inputs(master, contract['input_columns'])
```

시간·LOT로 학습/검증/시험을 먼저 나눈 뒤, 학습 부분에만 정상:이상 9:1을 적용하면 됨. Z-score 통계와 IF도 학습 구간에서만 맞춤. 시험 분포는 유지함. 아직 분할·언더샘플링·오버샘플링·모델 학습은 하지 않았음. 이 라벨로 얻은 성능은 우선 임시 규칙 재현 정도이며 실제 고장 탐지 성능으로 단정하지 않음.

## 실행과 결과 위치

01~06은 원본과 공통 코드로 독립 실행됨. 07은 05·06이 저장한 CSV를 읽음. 저장소 루트나 이 노트북 폴더에서 05 → 06 → 07 순서로 실행하면 됨. 노트북 출력은 비워서 저장함.

```text
data/processed/
├─ cal01_base_v1.csv        # 비교 기준표 하나
├─ classification/v1/      # 분류 입력 정의
├─ regression/v1/          # 회귀 입력 정의, 목표 미정
├─ features/v1/            # 06의 1분 파생 계산표
├─ review/v1/              # 제외·후보·정비 사건·라벨 근거
├─ analysis/               # maintenance / grade / signals 별 결과
├─ metadata/v1/            # 행 수·규칙·입력 컬럼·원본 해시
└─ archive/                # 이전 실험·중간표, 현재 학습에서 사용 안 함
```

라벨 세부 조건은 `metadata/v1/dataset.json`, 후보별 채택·미채택 이유와 실제 양성 구간은 `review/v1/weak_label_interval_decisions.csv`에 있음. BM·TBM·CBM과 부품의 left join은 `analysis/maintenance/v1/02_maintenance_events.csv`에서 확인함. 교체 없는 정비도 남김.

원본 CSV 7개는 `data/`에 두고, 그림은 `figures/namelesspark/`에 둠. 데이터 CSV는 Git에 올리지 않음. 원본·특징·라벨 규칙을 바꾸면 새 버전(v2 등)을 만들고 기존 기준표는 버전 보관 폴더로 옮김. 07은 같은 버전에서 입력 해시나 규칙이 달라지면 덮어쓰지 않고 중단함.

이전 CP 단독 trial v1·v2와 두 LOT 전체 수준 차이로 붙였던 라벨은 철회한 결과임. 현재 `cal01_base_v1`과 버전 체계가 다르며 `archive/retired_pre_v1/`에 격리함. 파일 삭제는 자동 승인 검토에서 차단되어 물리적으로 삭제하지 않았음.

## 기존 파일은 어디로 갔는지

| 기존 작업 | 정리한 위치 |
| --- | --- |
| `data_eda.ipynb` | 반복되는 파일 읽기·컬럼 확인은 제거하고 [원본 기록](reference/README.md)으로 연결 |
| `01_eda_4_event_overlap.ipynb` | 01의 전체 날짜 범위·실제 관측 중첩 확인으로 통합 |
| `02_eda_lot_grade_event_alignment.ipynb` | 01의 LOT·강종 연결로 통합. 종합 EDA의 실제 관측 경계 검증을 반영 |
| `04_equipment_master_timeseries_join_namelesspark.ipynb` | 01의 설비 태그·m:1 조인 검증으로 통합 |
| `03_feature_proposal_namelesspark.ipynb` | 정비·부품 내용은 02, LOT·강종 정의는 01로 모음. 반복 센서 그림은 후속 03·04를 기준으로 봄 |
| #71 `02_lot_comparison_namelesspark.ipynb` | 03으로 이동 |
| #71 `03_grade_comparison_namelesspark.ipynb` | 04로 이동 |
| 이전 `05_exclusion_windows_namelesspark.ipynb` | 최신 사용자 제외 조건과 판정 검토 역할로 05를 갱신. 과거 자동 제외 기준은 적용하지 않음 |
| #71 `01_feature_derivation_namelesspark.ipynb` | 06으로 이동. 파생 수식은 유지하고 최신 사용자 제외 조건을 적용 |
| 이전 파생변수·회귀·LOT별 상세 검토 | [참고 기록](reference/README.md)에 원본 버전을 연결해둠 |

현재 말투와 관찰 문장은 가능한 그대로 뒀음. 겹치는 설명은 한 곳으로 모으고, 새 번호와 달라진 기준이 필요한 부분만 보완했음.
