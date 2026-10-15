"""LOT 안의 지속적인 국소 변화 후보. 공정 허용치나 고장 라벨을 만들지 않음."""

import json

import numpy as np
import pandas as pd


SENSOR_COLUMNS = [
    "CLN-IN", "TC-Z1", "TC-Z2", "OP-Z1", "OP-Z2", "TC-Z3", "TC-Z4", "TC-Z5",
    "TC-Z6", "OP-Z3", "OP-Z4", "OP-Z5", "OP-Z6", "CP-Z4", "CP-Z4M", "TC-Z7",
    "TC-Z8", "TC-Z9", "OP-Z7", "OP-Z8", "TC-OUT1", "TC-OUT2",
]
TEMPORAL_REVIEW_RULES = {
    "version": "1.0",
    "reference": "이전 300초 유효 관측의 중앙값, 현재 시점 제외, 최소 60관측",
    "sustained_threshold": "max(6*잔차MAD시그마, 12*실제1초차분MAD시그마, 0.10*(LOT Q95-Q05), 부동소수점바닥)",
    "MAD_sigma": "1.4826 * median(abs(x-median(x)))",
    "duration": "같은 잔차 방향, 실제 1초 연속, END-START >= 10초 (최소 11관측)",
    "instant_summary_threshold": "max(12*실제1초차분MAD시그마, 3*Q99(abs(실제1초차분)), 0.25*(LOT Q95-Q05), 부동소수점바닥)",
    "periodicity": "연속 유효 1분 평균 구간의 선형 추세 제거 후 FFT; 최소 3주기, 주기>=3분, 최대주파수전력비>=0.25, 지연상관>=0.60",
    "limits": [
        "모든 문턱은 탐색 설정이며 공정 허용치나 정상·이상 정답이 아님",
        "전체 LOT로 구한 MAD·분위수·주기성은 사후 검토 통계이며 모델 입력에 그대로 사용하면 안 됨",
        "센서값·관측 공백은 보간하지 않으며 시간 공백이 지속 구간을 끊음",
        "TC 20도 왕복, OP 0·100, CP 공통 밴드를 단독 고장 규칙으로 사용하지 않음",
        "LOT 시작부터 유지된 수준 차이는 이 탐색으로 놓칠 수 있어 같은 강종의 다른 LOT와 별도 비교 필요",
        "주기·제어반응 표시는 정상 확정이 아니라 검토 맥락임",
    ],
}


def _sigma(values):
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    return float(1.4826 * np.median(np.abs(array - np.median(array)))) if len(array) else 0.0


def _strict_runs(mask, seconds):
    positions = np.flatnonzero(np.asarray(mask, dtype=bool))
    if not len(positions):
        return []
    splits = np.flatnonzero((np.diff(positions) != 1) | (np.diff(seconds[positions]) != 1)) + 1
    return np.split(positions, splits)


def _longest_run(mask, seconds):
    return max((int(seconds[run[-1]] - seconds[run[0]])
                for run in _strict_runs(mask, seconds)), default=0)


def _periodicity(series):
    minute = series.resample("1min").mean()
    valid = np.flatnonzero(minute.notna().to_numpy())
    blocks = np.split(valid, np.flatnonzero(np.diff(valid) != 1) + 1) if len(valid) else []
    result = {"PERIODIC_FLAG": False, "PERIOD_MIN": None, "POWER_SHARE": None,
              "LAG_CORR": None, "SEGMENT_MINUTES": 0}
    if not blocks:
        return result
    values = minute.iloc[max(blocks, key=len)].to_numpy()
    result["SEGMENT_MINUTES"] = len(values)
    if len(values) < 30:
        return result
    index = np.arange(len(values))
    values = values - np.polyval(np.polyfit(index, values, 1), index)
    if np.std(values) <= np.finfo(float).eps * max(1.0, abs(series.median())):
        return result
    frequencies = np.fft.rfftfreq(len(values), d=1)
    power = np.abs(np.fft.rfft(values)) ** 2
    eligible = (frequencies >= 3 / len(values)) & (frequencies <= 1 / 3)
    if not eligible.any():
        return result
    peak = np.flatnonzero(eligible)[np.argmax(power[eligible])]
    period = 1 / frequencies[peak]
    lag = int(round(period))
    share = float(power[peak] / power[1:].sum()) if power[1:].sum() else 0.0
    correlation = float(np.corrcoef(values[lag:], values[:-lag])[0, 1]) if lag < len(values) - 5 else np.nan
    result.update(PERIOD_MIN=float(period), POWER_SHARE=share, LAG_CORR=correlation,
                  PERIODIC_FLAG=bool(share >= 0.25 and correlation >= 0.60))
    return result


def _review_context(sensor, periodic, boundary):
    if sensor == "CP-Z4M":
        return "보조계측·생성관계 확인", "TC-Z5와의 중복성/생성 관계를 먼저 확인해야 함"
    if sensor.startswith("OP-"):
        return "제어반응·운전조건 확인", "출력의 급변·0·포화는 단독 고장 근거가 아니며 같은 존 TC·제어모드와 같이 검토해야 함"
    if periodic or sensor in ["TC-Z9", "TC-OUT1", "TC-OUT2"]:
        return "반복주기·운전패턴 확인", "반복 주기 또는 기존 주기채널 맥락이 있어 진폭·위상·운전조건을 함께 검토해야 함"
    if sensor == "TC-Z3":
        return "제어반응·운전조건 확인", "TC-Z3와 OP-Z3의 제어반응 맥락이며 20도 왕복만으로 이상을 정하지 않음"
    if boundary:
        return "LOT 경계 운전조건 확인", "관측 시작/끝 30분 이내로 운전단계·강종 전환·종료 준비 가능성을 함께 검토해야 함"
    return "이상 검토 우선", "해당 LOT·센서 자체의 변동 규모에 비해 큰 국소 변화임. 원인·정상 허용치는 미확정"


def build_temporal_review(retained, lot_context):
    """제외 후 원본으로 (지속 후보 표, LOT×센서 검토 범위 표)를 반환함.

    파일을 읽거나 쓰지 않음. 입력 객체를 변경하지 않고, 강종은 lot_context에서 받음.
    후보는 같은 방향 잔차가 실제 1초 간격으로 10초 이상 이어진 구간만 포함함.
    1초 급변은 coverage의 점 개수로만 남기며 지속 후보에 섞지 않음.
    """
    required = {"LOT_NO", "MEAS_DT", *SENSOR_COLUMNS}
    if not required.issubset(retained.columns):
        raise ValueError("LOT_NO, MEAS_DT와 원본 22개 계측이 필요함")
    if not {"LOT_NO", "GRADE"}.issubset(lot_context.columns) or lot_context.LOT_NO.duplicated().any():
        raise ValueError("LOT당 한 행인 LOT_NO·GRADE 연결표가 필요함")
    if retained.duplicated(["LOT_NO", "MEAS_DT"]).any():
        raise ValueError("같은 LOT·측정시각이 중복됨")
    if "EXCLUDED" in retained and retained.EXCLUDED.fillna(False).any():
        raise ValueError("사용자 제외 행을 먼저 제거한 retained를 넣어야 함")
    if retained.empty:
        raise ValueError("검토할 관측 행이 없음")
    if not pd.api.types.is_datetime64_any_dtype(retained.MEAS_DT):
        raise ValueError("MEAS_DT는 날짜형이어야 함")

    candidates, coverage = [], []
    for lot, group in retained.groupby("LOT_NO", sort=True):
        frame = group.sort_values("MEAS_DT").reset_index(drop=True)
        matching = lot_context.loc[lot_context.LOT_NO.eq(lot)]
        if len(matching) != 1 or pd.isna(matching.iloc[0].GRADE):
            raise ValueError(f"LOT {lot} 강종 연결 확인이 필요함")
        grade = matching.iloc[0].GRADE
        seconds = frame.MEAS_DT.to_numpy(dtype="datetime64[s]").astype("int64")
        exact = frame.MEAS_DT.diff().dt.total_seconds().eq(1)
        for sensor in SENSOR_COLUMNS:
            values = frame[sensor]
            series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(frame.MEAS_DT))
            difference = values.diff().where(exact)
            noise = _sigma(difference)
            q05, q95 = values.quantile([0.05, 0.95])
            width = float(q95 - q05)
            floor = np.finfo(float).eps * max(float(values.abs().max()), 1e-15) * 32
            baseline = series.rolling("300s", closed="left", min_periods=60).median().reset_index(drop=True)
            residual = values - baseline
            residual_sigma = _sigma(residual)
            threshold = max(6 * residual_sigma, 12 * noise, 0.10 * width, floor)
            instant_threshold = max(12 * noise, 3 * float(difference.abs().quantile(0.99)), 0.25 * width, floor)
            period = _periodicity(series)
            cov = {"LOT_NO": int(lot), "GRADE": grade, "SENSOR": sensor,
                   "RETAINED_ROWS": len(frame), "VALID_ROWS": int(values.notna().sum()),
                   "MISSING_ROWS": int(values.isna().sum()), "START": frame.MEAS_DT.min(), "END": frame.MEAS_DT.max(),
                   "MIN": float(values.min()), "Q05": float(q05), "MEDIAN": float(values.median()),
                   "Q95": float(q95), "MAX": float(values.max()), "MAX_EXACT_1S_ABS_CHANGE": float(difference.abs().max()),
                   "DIFF_ROBUST_SIGMA": noise, "RESIDUAL_ROBUST_SIGMA": residual_sigma,
                   "INSTANT_THRESHOLD": instant_threshold, "SUSTAINED_THRESHOLD": threshold,
                   "INSTANT_THRESHOLD_EXCEEDING_POINTS": int(difference.abs().gt(instant_threshold).sum()),
                   "BASELINE_VALID_ROWS": int(baseline.notna().sum()),
                   "MAX_CONTIGUOUS_VALID_S": _longest_run(values.notna(), seconds),
                   "MAX_CONTIGUOUS_ZERO_S": _longest_run(values.eq(0), seconds),
                   "MAX_CONTIGUOUS_GE100_S": _longest_run(values.ge(100), seconds) if sensor.startswith("OP-") else np.nan,
                   **period}
            coverage.append(cov)
            for kind, mask in [("local_deviation_high_10s", residual.gt(threshold)),
                               ("local_deviation_low_10s", residual.lt(-threshold))]:
                for indices in _strict_runs(mask.fillna(False), seconds):
                    elapsed = int(seconds[indices[-1]] - seconds[indices[0]])
                    if elapsed < 10:
                        continue
                    run_values = values.iloc[indices]
                    run_times = frame.MEAS_DT.iloc[indices]
                    run_residual = residual.iloc[indices]
                    start, end = run_times.iloc[0], run_times.iloc[-1]
                    boundary = ((start - frame.MEAS_DT.iloc[0]).total_seconds() <= 1800
                                or (frame.MEAS_DT.iloc[-1] - end).total_seconds() <= 1800)
                    category, reason = _review_context(sensor, period["PERIODIC_FLAG"], boundary)
                    stats = {
                        "start_value": float(run_values.iloc[0]), "end_value": float(run_values.iloc[-1]),
                        "min": float(run_values.min()), "median": float(run_values.median()), "max": float(run_values.max()),
                        "peak_to_peak": float(run_values.max() - run_values.min()), "observations": len(indices),
                        "threshold": threshold, "past5m_median_reference_median": float(baseline.iloc[indices].median()),
                        "median_residual": float(run_residual.median()), "max_abs_residual": float(run_residual.abs().max()),
                        "exact_1s_difference_robust_sigma": noise, "LOT_Q95_Q05_width": width,
                        "period_min": period["PERIOD_MIN"], "period_power_share": period["POWER_SHARE"],
                        "period_lag_corr": period["LAG_CORR"],
                    }
                    candidates.append({
                        "LOT_NO": int(lot), "GRADE": grade, "SENSOR": sensor, "START": start, "END": end,
                        "KIND": kind, "AMPLITUDE": float(run_residual.abs().max()), "DURATION_S": elapsed,
                        "OBSERVED_ROWS": len(indices), "MIN_VALUE": float(run_values.min()), "MAX_VALUE": float(run_values.max()),
                        "MEDIAN_VALUE": float(run_values.median()), "BASELINE_MEDIAN": float(baseline.iloc[indices].median()),
                        "THRESHOLD": threshold, "REVIEW_CATEGORY": category, "PERIODIC_CONTEXT": period["PERIODIC_FLAG"],
                        "LOT_BOUNDARY_CONTEXT": boundary, "FAULT_LABEL": pd.NA,
                        "EVIDENCE_REASON": reason + "; 통계적 탐색 후보이며 확정 이상 1이 아님",
                        "STATS": json.dumps(stats, ensure_ascii=False),
                    })

    coverage_df = pd.DataFrame(coverage)
    candidate_columns = ["LOT_NO", "GRADE", "SENSOR", "START", "END", "KIND", "AMPLITUDE", "DURATION_S",
                         "OBSERVED_ROWS", "MIN_VALUE", "MAX_VALUE", "MEDIAN_VALUE", "BASELINE_MEDIAN", "THRESHOLD",
                         "REVIEW_CATEGORY", "PERIODIC_CONTEXT", "LOT_BOUNDARY_CONTEXT", "FAULT_LABEL", "EVIDENCE_REASON", "STATS"]
    sustained_df = pd.DataFrame(candidates, columns=candidate_columns).sort_values(
        ["LOT_NO", "START", "SENSOR", "KIND"]).reset_index(drop=True)
    sustained_df.insert(0, "CANDIDATE_ID", [f"T{i:05d}" for i in range(1, len(sustained_df) + 1)])
    counts = sustained_df.groupby(["LOT_NO", "SENSOR"]).size()
    coverage_df["CANDIDATE_COUNT"] = [int(counts.get((row.LOT_NO, row.SENSOR), 0))
                                       for row in coverage_df.itertuples()]
    for (_, _), indices in coverage_df.groupby(["GRADE", "SENSOR"]).groups.items():
        for index in indices:
            others = coverage_df.loc[[other for other in indices if other != index], "MEDIAN"]
            coverage_df.loc[index, "SAME_GRADE_OTHER_LOTS"] = len(others)
            coverage_df.loc[index, "OTHER_LOT_MEDIANS_MEDIAN"] = others.median()
            coverage_df.loc[index, "MEDIAN_MINUS_OTHER_LOTS"] = coverage_df.loc[index, "MEDIAN"] - others.median()
    assert len(coverage_df) == retained.LOT_NO.nunique() * len(SENSOR_COLUMNS)
    assert not coverage_df.duplicated(["LOT_NO", "SENSOR"]).any()
    assert coverage_df.VALID_ROWS.add(coverage_df.MISSING_ROWS).eq(coverage_df.RETAINED_ROWS).all()
    assert sustained_df.DURATION_S.ge(10).all()
    assert sustained_df.OBSERVED_ROWS.eq(sustained_df.DURATION_S + 1).all()
    return sustained_df, coverage_df
