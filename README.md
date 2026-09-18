<div align="center">

# PDM PROJECT
### 설비 데이터를 점검과 보전의 근거로

[![CI](https://github.com/posco-3bungi-pdm/pdm-project/actions/workflows/ci.yml/badge.svg)](https://github.com/posco-3bungi-pdm/pdm-project/actions/workflows/ci.yml)
[작업 목록](https://github.com/posco-3bungi-pdm/pdm-project/issues) · [Pull requests](https://github.com/posco-3bungi-pdm/pdm-project/pulls) · [협업 안내](CONTRIBUTING.md)

</div>

---

## 프로젝트 소개

포스코 K-뉴딜 아카데미 팀 프로젝트입니다. 설비 데이터를 이해하고 이상 징후를 분석해 점검·보전 판단에 활용할 근거를 만듭니다.

**현재 단계: 프로젝트 착수.** 대상 설비, 최종 주제, 성공 기준은 팀 논의 후 [문제정의서](docs/01-problem-definition.md)에 기록합니다. 아직 분석 결과나 모델 성능을 검증한 상태는 아닙니다.

| 01 DEFINE | 02 UNDERSTAND | 03 COMPARE | 04 EXPLAIN |
| --- | --- | --- | --- |
| 문제·분석 단위 정의 | 데이터 품질·시간·그룹 확인 | 기준선과 모델 비교 | 경보 근거·한계·보전 조치 |

## 시작하기

Python 3.14를 기준으로 협업합니다. 다음 명령은 저장소 루트에서 실행합니다.

```powershell
git clone https://github.com/posco-3bungi-pdm/pdm-project.git
cd pdm-project
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-ci.txt
.\.venv\Scripts\python.exe -m nbstripout --install --attributes .gitattributes
.\.venv\Scripts\python.exe .github/scripts/check_repository.py
```

- `py -3.14`는 Windows의 Python 실행 관리자에게 3.14로 가상환경을 만들라고 지정합니다. 가상환경의 파이썬 버전은 만드는 순간 고정되므로, 버전을 바꾸려면 `.venv`를 지우고 다시 만듭니다.
- 가상환경은 만든 경로를 기억합니다. 프로젝트 폴더 이름을 바꾸거나 옮기면 `.venv\Scripts\pip.exe`와 `activate`가 깨지므로 `.venv`를 다시 만듭니다.
- 패키지 설치는 `python -m pip`로 실행합니다. 지금 켜져 있는 파이썬에 설치된다는 것이 명령에 드러납니다.
- `requirements.txt`는 분석용, `requirements-ci.txt`는 CI 검사용(`nbformat` 버전 고정)입니다. 로컬에 둘 다 설치하면 CI와 같은 버전으로 미리 검사할 수 있습니다.
- `nbstripout --install`은 이 저장소(`.git/config`)에만 필터를 등록합니다. 등록 후에는 `git add` 시점에 노트북 출력이 자동으로 제거됩니다. clone할 때마다 1회 실행해야 합니다.

마지막 줄은 **저장소 형식 검사**입니다. 분석 실행 명령은 주제와 의존성이 확정되면 이 문서에 추가합니다. 데이터 준비 방법은 [data/README.md](data/README.md)를 참고합니다.

## 폴더 안내

```text
.github/     Issue·PR 양식, 자동 검사와 자동 배정
data/        데이터 확보 안내 (원본은 Git에 올리지 않음)
docs/        문제 정의, 데이터 계약, 실험·의사결정 기록
notebooks/   탐색·시계열·모델·평가 노트북
src/         재사용하는 전처리·특징·모델 코드
tests/       분석 코드의 테스트
figures/     검토된 그래프
reports/     문제정의서, 결과보고서, 발표자료
```

## 팀 작업 흐름

**Issue → 작업 브랜치 → PR → CI → 동료 3명 이상 승인 → Squash merge**

- 작업을 시작하기 전에 목적과 완료 기준을 Issue에 적습니다.
- `main`은 함께 검토한 결과만 모으는 브랜치입니다.
- PR 작성자는 자신의 PR을 승인할 수 없습니다. 5인 팀에서 나머지 4명 중 3명이 승인합니다.
- 승인 후 새 커밋을 추가하면 다시 검토받습니다.
- PR의 `Closes #번호`로 작업 Issue를 연결합니다.

자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md), 자동화 설명은 [docs/automation.md](docs/automation.md)를 참고합니다.

## 분석의 기준

- 행 수와 독립 표본 수를 구분하고, 코일·버스트·세션 등 분석 단위를 먼저 정의합니다.
- 시간·그룹 기준으로 분할하고, 전처리 학습은 학습 구간에만 적용합니다.
- 단순 기준선과 모델을 같은 조건에서 비교합니다.
- 정답 라벨이 없으면 정확도·Recall·F1이나 실제 고장 예측 성능을 주장하지 않습니다.
- 결과에는 판단 근거, 경계 사례, 오탐 가능성, 현장 적용 한계를 함께 기록합니다.

## 데이터와 출처

원본 데이터와 수업 자료는 이 공개 저장소에 포함하지 않습니다. 데이터 사용 조건과 확보 경로를 먼저 확인합니다. P제철 배포본을 선택할 경우 교육용 재현 데이터라는 점을 명시하고 실제 기업 조업 데이터로 표현하지 않습니다.
