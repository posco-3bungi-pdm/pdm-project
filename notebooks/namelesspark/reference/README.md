# 이전 분석과 상세 근거

메인 01~07을 읽다가 이전 판단 과정을 확인할 때 보는 자료임.
같은 분석의 이전안을 전부 다시 복사하면 어느 기준이 최신인지 헷갈려서, 기존 Git 커밋의 원본으로 연결해둠. 아래 링크는 브랜치가 바뀌어도 같은 버전을 가리킴.

- [처음 데이터 열어본 기록](https://github.com/posco-3bungi-pdm/pdm-project/blob/7c53118d760ee8706bf34f7dc0dbd67549c8c286/notebooks/data_eda.ipynb): 현재 흐름과 겹치는 파일 읽기·컬럼 확인이라 실행용 사본은 두지 않음. 원래 메모는 이 버전에 남아 있음.
- [기존 종합 EDA](https://github.com/posco-3bungi-pdm/pdm-project/blob/7bfad00b972cc50c65e61497c3bc9dab846be796/notebooks/03_feature_proposal_namelesspark.ipynb): 정비·부품 분석과 초기 센서 탐색이 한 파일에 있었음. 현재 메인에서는 역할을 나눴음.
- [이전 파생변수 17개](https://github.com/posco-3bungi-pdm/pdm-project/blob/7bfad00b972cc50c65e61497c3bc9dab846be796/notebooks/04_feature_derivation_namelesspark.ipynb): 파생변수 아이디어를 확인할 때 참고함. 현재 메인 06과 연속 실행하는 단계가 아님. 전체기간 기준값이나 부품 기록 간격을 모델 입력으로 그대로 가져오지 않겠음.
- [이전 센서별 제외 구간](https://github.com/posco-3bungi-pdm/pdm-project/blob/c0f674fae5f414a356369026b7b0929ed28ece36/notebooks/05_exclusion_windows_namelesspark.ipynb): 분당 30개 관측 조건, 채널별 자동 제외 등을 검토했던 안임. 현재 메인 05의 네 시간 경계와 구분해서 봐야 함.
- [LOT별 상세 검토 14개](https://github.com/posco-3bungi-pdm/pdm-project/tree/c0f674fae5f414a356369026b7b0929ed28ece36/notebooks/07_lot_anomaly_review_namelesspark): 각 LOT의 확대 구간과 당시 해석을 확인하는 참고자료임. 과거의 30개 관측 기준 등은 현재 기준으로 확정된 게 아님.

센서별 회귀·잔차 실험은 로컬 `agent/exclusion-windows` 브랜치의 `480adaaba06da94d56f9420963866679e93a98a4` 커밋에 보존돼 있음. 그 안의 05·06은 당시 9/2/3 LOT 분할과 정상 후보 제외 규칙으로 수행한 별도 실험임. 이번 분류 흐름의 최종 라벨이나 검증 결과로 쓰지 않음.

LOT별 상세 검토 대상: 240001, 240024, 240037, 240038, 240044, 240058, 240061, 240069, 240091, 240108, 240114, 240117, 240121, 240133.

이번 정리에 가져온 #71 원본 버전은 `33bfa29e46bcb3efeb32bfc020ac015fb808ea1e`임. 최신 개인 폴더의 03·04·06은 그 버전의 시각화·파생변수 계산을 이어받았음.
