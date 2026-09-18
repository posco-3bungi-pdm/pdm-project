# 노트북

`01_eda.ipynb`, `02_timeseries.ipynb`, `03_model.ipynb`, `04_eval.ipynb` 순서를 권장합니다. 실제 분석이 시작될 때 생성합니다. 같은 파일은 한 명씩 맡고, 공통 로직은 `src/`로 옮깁니다. 커밋 전에 출력을 지우고 결과 그림은 검토 후 `figures/`에 저장합니다. `nbstripout` 필터를 등록해 두면 `git add` 시점에 출력이 자동으로 제거됩니다(등록 방법은 [README](../README.md) 시작하기 참고). 출력에는 `df.head()` 같은 원본 데이터 행이 그대로 남기 때문에 공개 저장소에서는 반드시 지우고 커밋합니다.
