"""구간별 정비 근거를 붙임. 결과는 검토용 sidecar이며 모델 입력이 아님."""

from pathlib import Path

import pandas as pd


def build_interval_maintenance_evidence(intervals, maintenance_context):
    """라벨 구간 또는 전체 후보에 05의 LOT 정비 문맥을 left join함.

    intervals: LOT_NO, START, END가 있는 DataFrame 또는 CSV 경로.
    maintenance_context: 05_lot_maintenance_evidence.csv 또는 그 DataFrame.

    반환행은 구간×WO임. 부품은 기존 WO별 집계 그대로 유지하며 재전개하지 않음.
    입력 구간 컬럼은 유지하고 정비 컬럼에는 MAINT_ 접두사를 붙임.
    DETC_MINUS_INTERVAL_*_H는 DETC_DT에서 구간 경계시각을 뺀 값임.
    양수는 해당 경계 뒤 감지, 음수는 경계 전 감지임. 작업시간 겹침은
    실제 설비 정지 또는 고장 지속을 뜻하지 않음. 구간은 [START, END],
    작업은 [STRT_DT, END_DT)로 비교함. 미래 정비·교체 결과는 X에서 제외함.
    """
    def read_frame(value):
        if isinstance(value, pd.DataFrame):
            return value.copy()
        if isinstance(value, (str, Path)):
            return pd.read_csv(value, encoding="utf-8-sig")
        raise TypeError("DataFrame 또는 CSV 경로가 필요함")

    left = read_frame(intervals)
    right = read_frame(maintenance_context)
    for frame, required, name in [
        (left, {"LOT_NO", "START", "END"}, "구간표"),
        (right, {"LOT_NO", "WO_NO", "DETC_DT", "STRT_DT", "END_DT", "MNT_TYPE"}, "정비 문맥표"),
    ]:
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name}에 필요한 컬럼이 없음: {sorted(missing)}")
        if not frame.columns.is_unique:
            raise ValueError(f"{name}에 중복 컬럼이 있음")
        if frame.LOT_NO.isna().any():
            raise ValueError(f"{name}의 LOT_NO가 비어 있음")

    reserved = {"EVIDENCE_INTERVAL_ROW", "_LOT_JOIN_KEY", "_EVIDENCE_MATCH"}
    if reserved.intersection(left.columns) or any(str(c).startswith("MAINT_") for c in left.columns):
        raise ValueError("구간표에 sidecar 예약 컬럼이 이미 있음")
    left["EVIDENCE_INTERVAL_ROW"] = range(len(left))
    left["_LOT_JOIN_KEY"] = pd.to_numeric(left.LOT_NO, errors="raise")
    right["_LOT_JOIN_KEY"] = pd.to_numeric(right.LOT_NO, errors="raise")
    if right.WO_NO.isna().any() or right.duplicated(["_LOT_JOIN_KEY", "WO_NO"]).any():
        raise ValueError("정비 문맥표는 LOT×WO당 한 행이어야 함. 부품 상세행으로 증식하면 안 됨")
    start = pd.to_datetime(left.START, errors="raise")
    end = pd.to_datetime(left.END, errors="raise")
    if start.isna().any() or end.isna().any() or start.gt(end).any():
        raise ValueError("구간 START/END가 비었거나 역전되어 있음")

    # 원본 날짜 표현과 구간 컬럼을 보존하고 계산만 datetime으로 수행함.
    right = right.drop(columns="LOT_NO").rename(
        columns={c: f"MAINT_{c}" for c in right.columns if c not in {"LOT_NO", "_LOT_JOIN_KEY"}}
    )
    result = left.merge(right, on="_LOT_JOIN_KEY", how="left", sort=False, indicator="_EVIDENCE_MATCH")
    result = result.sort_values("EVIDENCE_INTERVAL_ROW", kind="stable").reset_index(drop=True)
    has_record = result._EVIDENCE_MATCH.eq("both")
    if "GRADE" in result and "MAINT_GRADE" in result:
        mismatch = has_record & result.GRADE.notna() & result.MAINT_GRADE.notna() & result.GRADE.ne(result.MAINT_GRADE)
        if mismatch.any():
            raise ValueError("같은 LOT의 강종이 구간표와 정비 문맥표에서 다름")
    start = pd.to_datetime(result.START, errors="raise")
    end = pd.to_datetime(result.END, errors="raise")
    detc = pd.to_datetime(result.MAINT_DETC_DT, errors="raise")
    work_start = pd.to_datetime(result.MAINT_STRT_DT, errors="raise")
    work_end = pd.to_datetime(result.MAINT_END_DT, errors="raise")
    if (work_start.notna() & work_end.notna() & work_start.gt(work_end)).any():
        raise ValueError("정비 작업 시작/종료가 역전되어 있음")

    result["MAINT_CONTEXT_FOUND"] = has_record
    result["DETC_MINUS_INTERVAL_START_H"] = (detc - start).dt.total_seconds() / 3600
    result["DETC_MINUS_INTERVAL_END_H"] = (detc - end).dt.total_seconds() / 3600
    result["DETC_POSITION"] = "감지시각 없음"
    result.loc[detc.lt(start), "DETC_POSITION"] = "구간 전 감지"
    result.loc[detc.between(start, end), "DETC_POSITION"] = "구간 안 감지"
    result.loc[detc.gt(end), "DETC_POSITION"] = "구간 후 감지"
    result["DETC_INTERVAL_DISTANCE_H"] = 0.0
    result.loc[detc.lt(start), "DETC_INTERVAL_DISTANCE_H"] = ((start - detc).dt.total_seconds() / 3600)
    result.loc[detc.gt(end), "DETC_INTERVAL_DISTANCE_H"] = ((detc - end).dt.total_seconds() / 3600)
    result.loc[detc.isna(), "DETC_INTERVAL_DISTANCE_H"] = float("nan")
    result["FUTURE_DETECTION_AT_INTERVAL_START"] = detc.gt(start).astype("boolean").mask(detc.isna())
    result["FUTURE_WORK_END_AT_INTERVAL_END"] = work_end.gt(end).astype("boolean").mask(work_end.isna())
    known_work = work_start.notna() & work_end.notna()
    result["WORK_INTERVAL_OVERLAP"] = (
        work_start.le(end) & work_end.gt(start) & work_end.gt(work_start)
    ).astype("boolean").mask(~known_work)
    result["MODEL_INPUT_ALLOWED"] = False
    result["CONFIRMS_SENSOR_FAULT"] = False
    result["PART_REPLACEMENT_TIMESTAMP_KNOWN"] = False
    result["EVIDENCE_SCOPE"] = "LOT 정비 문맥; 구간과의 시간 관계를 추가한 사후 검토용"
    result["EVIDENCE_SOURCE"] = "05_lot_maintenance_evidence.csv"
    result["EVIDENCE_NOTE"] = (
        "정비 시각이 가깝거나 부품이 교체됐다는 사실만으로 이 센서 변화의 원인을 확정하지 않음. "
        "DOWN_MIN은 해당 정비의 정지분량이며 작업시간과 다름. 정확한 정지구간·교체시각은 역산하지 않음. "
        "정지 0분은 다른 원인 정지가 없었다는 증거가 아님. 사후 감지·작업·교체 결과는 모델 입력 금지임."
    )
    return result.drop(columns=["_LOT_JOIN_KEY", "_EVIDENCE_MATCH"])
