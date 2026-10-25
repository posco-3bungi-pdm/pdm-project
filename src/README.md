# 실행 코드

- `build_report.py`: [결과보고서](../reports/결과보고서.md)를 HTML과 PDF로 만듦
- `check_delivery.py`: 문서 링크와 저장된 모델 지표를 검사함
- `plot_report_cases.py`: 저장된 v7 데이터와 모델 예측으로 보고서 사례 그림 4개를 만듦

전처리와 모델 학습은 [기존 노트북](../notebooks/README.md)에 그대로 있음.
이번 정리에서 계산을 다른 파일로 옮기거나 다시 학습하지 않았음.

저장소 루트에서 실행함.

```bash
python src/check_delivery.py
python src/check_delivery.py --results-dir data/processed/model_results
python -m unittest discover -s tests -v
python src/build_report.py
python src/plot_report_cases.py
```

HTML은 `build/reports/`에 생성됨.
`build/`는 작업 폴더이므로 Git에 올리지 않음.

PDF가 필요하면 PyMuPDF와 Microsoft Edge를 사용함.

```bash
python -m pip install -r requirements-report.txt
python src/build_report.py --pdf
```

Edge 설치 위치가 다르면 `--edge`에 실행 파일을 지정함.
공개할 PDF는 검토 후 [reports](../reports/)에 옮김.
