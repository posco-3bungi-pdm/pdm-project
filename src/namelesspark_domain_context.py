"""검토 구간에 원본 도메인 기록을 연결함. 이상 판정이나 모델 입력은 만들지 않음."""

import pandas as pd


CAL_TAG = "P1-CR1-CAL01"


def _nearby(records, start, end, start_col, end_col=None):
    """가장 가까운 전/후 기록(동률 포함)과 겹치는 모든 기록을 반환함."""
    if records.empty:
        return [(None, relation, None) for relation in ["before", "overlap", "after"]]
    starts = pd.to_datetime(records[start_col], errors="raise")
    ends = starts if end_col is None else pd.to_datetime(records[end_col], errors="raise")
    if starts.isna().any() or ends.isna().any() or ends.lt(starts).any():
        raise ValueError("근거 기록의 시작·종료시각을 확인해야 함")
    # 작업은 [시작, 종료), 조업/감지는 한 시점임. 후보 END는 마지막 실제 관측임.
    point = ends.eq(starts)
    before = ends.lt(start) | (ends.eq(start) & ~point)
    after = starts.gt(end)
    overlap = ~(before | after)
    chosen = []
    for relation, mask in [("before", before), ("overlap", overlap), ("after", after)]:
        subset = records.loc[mask]
        if subset.empty:
            chosen.append((None, relation, None))
            continue
        if relation == "before":
            subset = subset.loc[ends.loc[subset.index].eq(ends.loc[subset.index].max())]
        elif relation == "after":
            subset = subset.loc[starts.loc[subset.index].eq(starts.loc[subset.index].min())]
        for idx, row in subset.iterrows():
            gap = ((start - ends.loc[idx]) if relation == "before" else
                   (starts.loc[idx] - end) if relation == "after" else pd.Timedelta(0))
            chosen.append((row, relation, gap.total_seconds() / 3600))
    return chosen


def build_domain_context(intervals, sources, maintenance, lot_context):
    """구간×근거 long table을 반환함. 원본 및 입력 DataFrame을 변경하지 않음.

    BM/TBM/CBM별 작업·감지, CR1 정기수리, 조업이벤트 유형별 직전/중/직후를
    보존함. 가까움은 인과관계가 아니므로 일률적인 ±N일 문턱을 사용하지 않음.
    정기수리는 원본 자정 END_DT 기준과 종료일 포함 가정을 따로 표시함.
    SOURCE_*는 원본 필드이며 사후 검토용임. 학습 특징으로 사용하면 안 됨.
    """
    required = {"LOT_NO", "GRADE", "SENSOR", "START", "END"}
    if not required.issubset(intervals.columns):
        raise ValueError(f"구간 필수 컬럼 누락: {sorted(required - set(intervals.columns))}")
    candidates = intervals.copy().reset_index(drop=True)
    for c in ["START", "END"]:
        candidates[c] = pd.to_datetime(candidates[c], errors="raise")
    if candidates[["START", "END"]].isna().any().any() or candidates.END.lt(candidates.START).any():
        raise ValueError("구간 시작·종료시각이 유효하지 않음")
    if "INTERVAL_ID" not in candidates:
        candidates["INTERVAL_ID"] = [f"CTX-{i:04d}" for i in range(1, len(candidates) + 1)]
    if candidates.INTERVAL_ID.isna().any() or candidates.INTERVAL_ID.duplicated().any():
        raise ValueError("INTERVAL_ID가 고유해야 함")
    lots = lot_context.set_index("LOT_NO", verify_integrity=True)
    events = sources["event"].loc[sources["event"].PLANT_CD.eq("CR1")].copy()
    repair = sources["repair"].loc[sources["repair"].PLANT_CD.eq("CR1")].copy()
    equipment = sources["eqp"].loc[sources["eqp"].EQP_TAG.eq(CAL_TAG)].copy()
    maint = maintenance.loc[maintenance.EQP_TAG.eq(CAL_TAG)].copy()
    if maint.WO_NO.duplicated().any() or len(equipment) > 1:
        raise ValueError("정비 집계 WO_NO 또는 대상 설비마스터가 중복됨")
    rows = []
    for interval in candidates.itertuples(index=False):
        if interval.LOT_NO not in lots.index:
            raise ValueError(f"LOT 관측 정보 없음: {interval.LOT_NO}")
        lot = lots.loc[interval.LOT_NO]
        if interval.GRADE != lot.GRADE or interval.START < lot.START or interval.END > lot.END:
            raise ValueError(f"LOT 강종/실제 관측 범위와 후보가 다름: {interval.LOT_NO}")
        base = {c: getattr(interval, c) for c in ["INTERVAL_ID", "LOT_NO", "GRADE", "SENSOR", "START", "END"]}
        for field in ["CANDIDATE_ID", "KIND", "AMPLITUDE", "DURATION_S", "THRESHOLD",
                      "MIN_VALUE", "MAX_VALUE", "BASELINE_MEDIAN", "REVIEW_CATEGORY",
                      "PERIODIC_CONTEXT", "LOT_BOUNDARY_CONTEXT", "EVIDENCE_REASON"]:
            if hasattr(interval, field):
                base[field if field == "CANDIDATE_ID" else f"CANDIDATE_{field}"] = getattr(interval, field)
        base.update(LOT_START=lot.START, LOT_END=lot.END, LOT_ROWS=lot.ROWS,
                    STATUS="review", CAUSALITY_CONFIRMED=False)

        def emit(record, kind, source_file, source_id, relation, gap, reason, timing=""):
            output = dict(base, SOURCE_KIND=kind, SOURCE_FILE=source_file,
                          SOURCE_ID=None if record is None else record[source_id],
                          RELATION=relation, GAP_HOURS=gap, TIMING_BASIS=timing,
                          EVIDENCE_FOUND=record is not None, EVIDENCE_REASON=reason)
            if record is not None:
                output.update({f"SOURCE_{k}": v for k, v in record.items()})
            rows.append(output)

        emit(None if equipment.empty else equipment.iloc[0], "equipment", "G-01_설비마스터.csv",
             "EQP_TAG", "metadata", None,
             "온도 CSV 대상 CAL01의 설비 정보임. 센서별 위치·단위·설정값 마스터는 원본에 없음")
        for category in sorted(set(["BM", "TBM", "CBM"]) | set(maint.MNT_TYPE.dropna())):
            records = maint.loc[maint.MNT_TYPE.eq(category)]
            for kind, time_col, end_col in [("maintenance_work", "STRT_DT", "END_DT"),
                                             ("maintenance_detection", "DETC_DT", None)]:
                for record, relation, gap in _nearby(records, interval.START, interval.END, time_col, end_col):
                    reason = f"{category} {relation} 기록 없음"
                    if record is not None:
                        reason = (f"{category} {relation}: {record.WO_NO}; 감지 {record.DETC_DT}; "
                                  f"작업 {record.STRT_DT}~{record.END_DT}; 고장코드 {record.FAIL_MODE}; "
                                  f"기록 {record.REMARK}; 부품 {record.get('PART_NAMES', '') or '교체 기록 없음'}; "
                                  f"교체사유 {record.get('PART_CHANGE_REASONS', '')}; DOWN_MIN={record.DOWN_MIN}. "
                                  "시간상 근접·겹침이며 센서 변화의 원인 확정 아님. 정지 시점은 역산하지 않음")
                    emit(record, kind, "G-02_정비이력.csv | G-02_부품교체이력.csv | G-01_부품마스터.csv",
                         "WO_NO", relation, gap, reason, f"{category}: {time_col}" + ("~END_DT [시작,종료)" if end_col else " 시점"))
        for include_end_date in [False, True]:
            calendar = repair.copy()
            calendar["CONTEXT_END"] = calendar.END_DT + (pd.Timedelta(days=1) if include_end_date else pd.Timedelta(0))
            basis = "종료일 포함 가정; END_DT 다음 날 자정까지" if include_end_date else "원본 END_DT 자정까지"
            for record, relation, gap in _nearby(calendar, interval.START, interval.END, "STRT_DT", "CONTEXT_END"):
                reason = "해당 방향의 CR1 정기수리 기록 없음"
                if record is not None:
                    reason = f"{record.PLAN_ID}: {record.SCOPE}; {basis}. 예정 범위이며 실제 정지·작업 이행 여부는 이 표만으로 확정 불가"
                emit(record, "repair_calendar", "G-01_정기수리캘린더.csv", "PLAN_ID", relation, gap, reason, basis)
        event_types = sorted(events.EVT_TYPE.dropna().unique()) or [None]
        for event_type in event_types:
            records = events.loc[events.EVT_TYPE.eq(event_type)]
            for record, relation, gap in _nearby(records, interval.START, interval.END, "EVT_DT"):
                reason = f"CR1 {event_type} {relation} 기록 없음"
                if record is not None:
                    reason = f"{record.EVT_ID}: {record.EVT_TYPE} {record.BEF_VAL}→{record.AFT_VAL}; 운전 조건 맥락이며 센서 이상 원인 확정 아님"
                emit(record, "operation_event", "G-02_조업이벤트.csv", "EVT_ID", relation, gap, reason, f"{event_type}: EVT_DT 시점")
    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=["CONTEXT_ROW_ID", "INTERVAL_ID", "LOT_NO", "GRADE", "SENSOR",
                                     "START", "END", "SOURCE_KIND", "SOURCE_ID", "RELATION",
                                     "GAP_HOURS", "EVIDENCE_FOUND", "EVIDENCE_REASON", "STATUS"])
    if not result.empty:
        if set(result.INTERVAL_ID) != set(candidates.INTERVAL_ID):
            raise AssertionError("근거 없는 후보도 남아 있어야 함")
        result.insert(0, "CONTEXT_ROW_ID", [f"DCTX-{i:05d}" for i in range(1, len(result) + 1)])
    return result
