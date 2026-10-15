"""철회된 CP 규칙 실험 기록. 전체 센서의 도메인 검증 라벨 생성에 사용하지 않음."""

import numpy as np
import pandas as pd


VERSION = "trial_v2_cp_only_20261015"
# 동일 강종 비교와 05 검토를 거쳐 이번 실험의 참조로 선택한 LOT임.
# 정상 설비로 현장 확인됐다는 뜻이 아니며, 새 데이터에 자동 적용하지 않음.
REFERENCE_LOTS = (240024, 240037, 240044, 240069, 240108)
DEFERRED_LEVEL_LOTS = (240091, 240121)  # 설정값·허용편차 확인 전 수준 차이는 판정 보류.
CP_THRESHOLD_MULTIPLIER = 2.0  # 05의 국소 이탈 탐색 문턱보다 강한 구간만 선택.
CP_LOT_SIGMA_MULTIPLIER = 12.0  # 기준선 지연으로 생기는 정상 수준 복귀 후보는 제외.
GRAY_BUFFER_SECONDS = 60


def build_trial_training(frame, sustained, maintenance, past_features, *, allow_unvalidated_cp_experiment=False):
    """원본 시점 특징표를 받아 숫자 학습표·행별 근거·검토 요약을 반환함.

    0 = 이번 검토에서 선택한 참조 LOT의 미해결 후보 밖 관측행.
    1 = 강한 CP 지속 이탈의 실험 후보. 수준 차이만으로는 1을 만들지 않음.
    그 외는 NA로 남겨 학습에서 제외함. 사후 정비값은 입력으로 넣지 않음.
    """
    if not allow_unvalidated_cp_experiment:
        raise ValueError("CP 규칙 라벨은 도메인 검증 학습표로 철회됨. 05의 사건 근거를 판정한 구간만 07에서 사용해야 함")
    review = frame.sort_values(["LOT_NO", "MEAS_DT"]).reset_index(drop=True).copy()
    review["TRIAL_LABEL"] = pd.Series(pd.NA, index=review.index, dtype="Int8")
    review["TRIAL_REASON"] = "강종·운전조건 또는 센서 변화의 판정 보류"
    review["TRIAL_RULE"] = "defer"
    reference = review.LOT_NO.isin(REFERENCE_LOTS)
    review.loc[reference, "TRIAL_LABEL"] = 0
    review.loc[reference, "TRIAL_REASON"] = "동일 강종 비교용 참조 LOT; 미해결 후보·정비 작업 구간을 뺀 실험 정상"
    review.loc[reference, "TRIAL_RULE"] = "reference_without_unresolved_candidates"

    # 후보 주변을 0으로 학습하지 않도록 비워둠. 후보를 자동으로 1로 만들지는 않음.
    gray = np.zeros(len(review), dtype=bool)
    for row in sustained.itertuples(index=False):
        if row.SENSOR == "CP-Z4M":
            continue  # 의미 미확인 보조계측은 입력·정답 정의에서 제외.
        hit = review.LOT_NO.eq(row.LOT_NO) & review.MEAS_DT.between(
            pd.Timestamp(row.START) - pd.Timedelta(seconds=GRAY_BUFFER_SECONDS),
            pd.Timestamp(row.END) + pd.Timedelta(seconds=GRAY_BUFFER_SECONDS),
        )
        gray |= hit.to_numpy()
    review.loc[reference & gray, "TRIAL_LABEL"] = pd.NA
    review.loc[reference & gray, "TRIAL_REASON"] = "미해결 센서 후보 및 앞뒤 60초; 정상으로 자동 배정하지 않음"
    review.loc[reference & gray, "TRIAL_RULE"] = "unresolved_temporal_candidate"

    intervals = []
    level_deferred = review.LOT_NO.isin(DEFERRED_LEVEL_LOTS)
    review.loc[level_deferred, "TRIAL_REASON"] = "TC-Z7/Z8 수준 차이는 있으나 설정값·운전조건·허용편차 미확인; 0/1 판정 보류"
    review.loc[level_deferred, "TRIAL_RULE"] = "unconfirmed_level_shift_defer"
    assert review.loc[level_deferred, "TRIAL_LABEL"].isna().all()

    strong_cp = sustained.loc[
        sustained.SENSOR.eq("CP-Z4")
        & sustained.LOT_NO.isin(REFERENCE_LOTS)
        & sustained.KIND.isin(["local_deviation_high_10s", "local_deviation_low_10s"])
        & sustained.AMPLITUDE.ge(CP_THRESHOLD_MULTIPLIER * sustained.THRESHOLD)
    ]
    cp_centers = review.groupby("LOT_NO")["CP-Z4"].median()
    cp_scales = review.groupby("LOT_NO")["CP-Z4"].agg(lambda s: 1.4826 * (s - s.median()).abs().median())
    for row in strong_cp.itertuples(index=False):
        hit = review.LOT_NO.eq(row.LOT_NO) & review.MEAS_DT.between(row.START, row.END)
        centered = review["CP-Z4"] - cp_centers.loc[row.LOT_NO]
        threshold = CP_LOT_SIGMA_MULTIPLIER * cp_scales.loc[row.LOT_NO]
        hit &= centered.gt(threshold) if "high" in row.KIND else centered.lt(-threshold)
        indices = np.flatnonzero(hit.to_numpy())
        if not len(indices):
            continue
        seconds = review.loc[indices, "MEAS_DT"].to_numpy(dtype="datetime64[s]").astype("int64")
        cuts = np.flatnonzero((np.diff(indices) != 1) | (np.diff(seconds) != 1)) + 1
        for selected in np.split(indices, cuts):
            if len(selected) < 11:
                continue
            times = review.loc[selected, "MEAS_DT"]
            reason = "CP 국소 이탈 및 LOT 중앙값 대비 12×MADσ 초과가 1초 간격 10초 이상 지속; 정상 수준 복귀는 제외한 실험 후보"
            review.loc[selected, "TRIAL_LABEL"] = 1
            review.loc[selected, "TRIAL_REASON"] = reason
            review.loc[selected, "TRIAL_RULE"] = "strong_CP_local_deviation"
            intervals.append({"LOT_NO": row.LOT_NO, "GRADE": row.GRADE, "START": times.iloc[0], "END": times.iloc[-1],
                              "SENSOR": row.SENSOR, "RULE": "strong_CP_local_deviation",
                              "MATCHED_ROWS": len(selected), "REASON": reason,
                              "INTERVAL_ROLE": "실제 1초 간격 10초 이상 관측한 국소 이탈 구간"})

    # 작업 중이라는 사실만으로 정상/이상을 정하지 않음. 정지 구간을 역산하지도 않음.
    work_overlap = np.zeros(len(review), dtype=bool)
    for work in maintenance.itertuples(index=False):
        work_overlap |= (review.MEAS_DT.ge(work.STRT_DT) & review.MEAS_DT.lt(work.END_DT)).to_numpy()
    review.loc[work_overlap, "TRIAL_LABEL"] = pd.NA
    review.loc[work_overlap, "TRIAL_REASON"] = "정비 작업 겹침; 실제 정지 시점과 운전 모드 미확정"
    review.loc[work_overlap, "TRIAL_RULE"] = "maintenance_work_overlap_defer"

    sensors = [c for c in frame.columns if c.startswith(("TC-", "OP-")) and "_" not in c]
    sensors += ["CLN-IN", "CP-Z4"]
    numeric_features = [*sensors, "LOT_ELAPSED_MIN", *past_features]
    assert len(sensors) == 21 and len(set(numeric_features)) == len(numeric_features)
    feature_valid = np.isfinite(review[numeric_features].to_numpy(dtype=float)).all(axis=1)
    review["TRAIN_INCLUDED"] = review.TRIAL_LABEL.notna() & feature_valid
    review["LABEL_VERSION"] = VERSION
    review["LABEL_STATUS"] = "실험용 규칙 라벨; 현장 확정 정답 아님"
    chosen = review.loc[review.TRAIN_INCLUDED].copy()
    model = chosen[numeric_features].reset_index(drop=True)
    grades = sorted(review.GRADE.unique())
    for grade in grades:
        model[f"GRADE_{grade}"] = chosen.GRADE.eq(grade).to_numpy(dtype="int8")
    model["LABEL"] = chosen.TRIAL_LABEL.to_numpy(dtype="int8")
    model.index.name = None
    audit = chosen[["LOT_NO", "MEAS_DT", "GRADE", "TRIAL_LABEL", "TRIAL_RULE", "TRIAL_REASON",
                    "LABEL_VERSION", "LABEL_STATUS"]].rename(columns={"TRIAL_LABEL": "LABEL"}).reset_index(drop=True)
    audit.insert(0, "CSV_ROW_INDEX", np.arange(len(audit)))
    assert len(model) == len(audit) and model.LABEL.nunique() == 2
    assert np.isfinite(model.to_numpy(dtype=float)).all()
    assert not {"LOT_NO", "MEAS_DT", "DOWN_MIN", "TRIAL_RULE", "TRIAL_REASON", "CP-Z4M"}.intersection(model.columns)
    interval_table = pd.DataFrame(intervals).sort_values(["LOT_NO", "START", "SENSOR"]).reset_index(drop=True)
    interval_table.insert(0, "INTERVAL_ID", [f"V2-{i:04d}" for i in range(1, len(interval_table) + 1)])
    interval_table = interval_table.rename(columns={"MATCHED_ROWS": "MATCHED_ROWS_BEFORE_FINAL_FILTER"})
    interval_table["TRAIN_INCLUDED_ROWS"] = [
        int((review.TRAIN_INCLUDED & review.TRIAL_LABEL.eq(1).fillna(False)
             & review.LOT_NO.eq(row.LOT_NO) & review.MEAS_DT.between(row.START, row.END)
             & review.TRIAL_RULE.eq(row.RULE)).sum())
        for row in interval_table.itertuples(index=False)
    ]
    assert int(interval_table.TRAIN_INCLUDED_ROWS.sum()) == int(model.LABEL.eq(1).sum())
    counts = audit.groupby(["LOT_NO", "GRADE", "LABEL"]).size().unstack("LABEL", fill_value=0).rename(columns={0:"NORMAL_0",1:"ANOMALY_1"}).reset_index()
    summary = {
        "label_version": VERSION, "label_status": "실험용 규칙 라벨; 현장 확정 고장 정답 아님",
        "retained_rows": len(review), "training_rows": len(model),
        "normal_0": int(model.LABEL.eq(0).sum()), "anomaly_1": int(model.LABEL.eq(1).sum()),
        "deferred_rows": int(review.TRIAL_LABEL.isna().sum()),
        "labeled_but_feature_missing_rows": int((review.TRIAL_LABEL.notna() & ~feature_valid).sum()),
        "input_feature_count": len(model.columns)-1, "input_columns": model.columns.drop("LABEL").tolist(),
        "reference_lots": list(REFERENCE_LOTS), "deferred_level_lots": list(DEFERRED_LEVEL_LOTS),
        "oversampling_applied": False, "undersampling_applied": False,
        "cp_threshold_multiplier": CP_THRESHOLD_MULTIPLIER,
        "cp_lot_sigma_multiplier": CP_LOT_SIGMA_MULTIPLIER,
        "gray_buffer_seconds": GRAY_BUFFER_SECONDS,
        "zero_definition": "선정한 참조 LOT에서 미해결 후보·작업 구간을 뺀 관측행; 현장 정상 확정 아님",
        "one_definition": "강한 CP 10초 이상 국소 이탈; 이전 2522행의 고정범위 규칙과 다름",
        "limitations": ["전체 센서 검토 중 애매한 유형은 0으로 채우지 않고 제외함", "사후 관측을 참고한 규칙 라벨이므로 규칙 재현 성능과 고장 예측 성능은 다름", "전체 관측을 보고 규칙을 정했으므로 이후 시간·LOT 분할만으로 독립 고장 검증이 되지 않음; 별도 미검토 사건 평가가 필요함", "시간·LOT 단위 분할이 필요하며 아직 분할하거나 모델을 학습하지 않음", "현재 로컬 센서값은 판정 시점에 관측된 값이며 미래 고장 예측용 표가 아님"],
    }
    return model, audit, review, interval_table, counts, summary
