# 자동화가 확인하는 것

| 기능 | 언제 실행되는가 | 하는 일 |
| --- | --- | --- |
| CI / Repository checks | PR, main push, 수동 실행 | 파일 정책, Python 문법, 노트북 형식, 문서 링크, 보고서 생성과 지표 계산 검사 |
| nbstripout git 필터 | 로컬 `git add` | 노트북 출력·실행 번호를 커밋 사본에서 자동 제거 (clone 후 1회 등록) |
| Assign new issues | 새 Issue | Write 이상 권한을 가진 작성자에게 자동 배정 |
| Dependabot | 매주 | Actions·CI 패키지 업데이트 PR 생성 |

## CI의 범위

원본 데이터 없이 실행함.
파일 정책과 노트북 형식은 `.github/scripts/check_repository.py`로 검사함.
문서의 로컬 링크는 `src/check_delivery.py`, 보고서 생성과 지표 계산은 `tests/`로 검사함.
CI는 `python -m unittest discover -s tests -v`도 실행함.

모델을 다시 학습하지 않으므로 성능이나 현장 고장 탐지 정확성을 보장하지 않음.
저장된 로컬 CSV의 지표까지 확인하려면 `python src/check_delivery.py --results-dir data/processed/model_results`를 실행함.

## 자동 배정

이미 담당자가 있으면 유지합니다. 외부 작성자와 봇은 자동 배정하지 않습니다. 텍스트를 셸 명령으로 실행하지 않고 GitHub 이벤트 객체를 API 입력으로 사용합니다. 권한은 해당 작업에 필요한 읽기와 Issue 쓰기로 한정합니다.

## Rulesets

`main`의 병합 조건은 동료 3명 승인, 최신 커밋에 대한 승인, 미해결 대화 없음, `Repository checks` 성공입니다. main이 먼저 변경되면 브랜치를 최신화한 뒤 검사를 다시 실행합니다. 관리자도 우회 목록에 넣지 않습니다.

GitHub Free 공개 저장소에서 사용할 수 있는 저장소 단위 Ruleset을 사용합니다. 조직 단위 일괄 Ruleset은 별도 유료 플랜 기능입니다.
