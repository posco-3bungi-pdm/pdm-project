"""개인 분석 노트북에서 같이 쓰는 데이터 연결 기준. 이상 라벨은 만들지 않음."""

from pathlib import Path

import pandas as pd


CAL_TAG = "P1-CR1-CAL01"
USER_EXCLUSIONS = (
    (240058, "2024-06-09 08:00:00", "at_or_after", "사용자 지정: 노 내림 구간 제외"),
    (240061, "2024-06-15 02:30:00", "before", "사용자 지정: 승온 구간 제외"),
    (240114, "2024-11-04 20:00:00", "at_or_after", "사용자 지정: 정기수리 전 하강 구간 제외"),
    (240117, "2024-11-13 09:00:00", "before", "사용자 지정: 정기수리 후 승온 구간 제외"),
)


def load_sources(root):
    """원본을 읽고 날짜형만 맞춤. 행 삭제나 결측 보간은 하지 않음."""
    specs = {
        "temp": ("T-CR1-CAL01_온도.csv", ["MEAS_DT"]),
        "event": ("G-02_조업이벤트.csv", ["EVT_DT"]),
        "repair": ("G-01_정기수리캘린더.csv", ["STRT_DT", "END_DT"]),
        "eqp": ("G-01_설비마스터.csv", ["INSTALL_DT"]),
        "part": ("G-01_부품마스터.csv", []),
        "maint": ("G-02_정비이력.csv", ["DETC_DT", "STRT_DT", "END_DT"]),
        "partchg": ("G-02_부품교체이력.csv", []),
    }
    data = Path(root) / "data"
    result = {}
    for key, (filename, dates) in specs.items():
        frame = pd.read_csv(data / filename, encoding="utf-8-sig")
        for column in dates:
            frame[column] = pd.to_datetime(frame[column], errors="raise")
        result[key] = frame
    return result


def build_lot_context(temp, event):
    """LOT의 실제 관측 범위와 시작시각에 일치하는 CR1 강종을 연결함."""
    if temp.duplicated(["LOT_NO", "MEAS_DT"]).any():
        raise ValueError("LOT_NO·MEAS_DT 중복을 먼저 확인해야 함")
    lots = temp.groupby("LOT_NO", as_index=False).agg(
        START=("MEAS_DT", "min"), END=("MEAS_DT", "max"), ROWS=("MEAS_DT", "size")
    )
    changes = event.loc[
        event["PLANT_CD"].eq("CR1") & event["EVT_TYPE"].eq("강종변경"),
        ["EVT_DT", "BEF_VAL", "AFT_VAL"],
    ].sort_values("EVT_DT")
    if changes["EVT_DT"].duplicated().any():
        raise ValueError("같은 시각의 CR1 강종변경이 여러 건임")
    lots = lots.merge(
        changes[["EVT_DT", "AFT_VAL"]], left_on="START", right_on="EVT_DT",
        how="left", validate="many_to_one",
    ).rename(columns={"AFT_VAL": "GRADE"}).drop(columns="EVT_DT")
    if lots["GRADE"].isna().any():
        raise ValueError("LOT 첫 관측시각과 일치하는 강종변경이 없음. 가까운 시각으로 대신 붙이지 않음")
    for lot in lots.itertuples():
        during = changes.loc[changes["EVT_DT"].gt(lot.START) & changes["EVT_DT"].le(lot.END)]
        if not during.empty:
            raise ValueError(f"LOT {lot.LOT_NO} 실제 관측 구간 안에 강종변경이 있음")
        following = changes.loc[changes["EVT_DT"].gt(lot.END)]
        if not following.empty and following.iloc[0]["BEF_VAL"] != lot.GRADE:
            raise ValueError(f"LOT {lot.LOT_NO} 강종과 다음 변경의 BEF_VAL이 다름")
    lots["DURATION_H"] = (lots["END"] - lots["START"]).dt.total_seconds() / 3600
    return lots[["LOT_NO", "GRADE", "START", "END", "ROWS", "DURATION_H"]].sort_values("START").reset_index(drop=True)


def build_maintenance_context(maint, partchg, part):
    """정비 1건당 1행인 전체 표와 교체 부품별 상세 표를 따로 돌려줌.

    PART_*는 사후 검토 정보임. 센서 시점의 모델 입력으로 바로 쓰면 안 됨.
    """
    if maint["WO_NO"].duplicated().any() or part["PART_CD"].duplicated().any():
        raise ValueError("정비 WO_NO와 부품마스터 PART_CD가 각각 고유해야 함")
    if not partchg["WO_NO"].isin(maint["WO_NO"]).all():
        raise ValueError("정비이력에 없는 부품교체 WO_NO가 있음")
    events = maint.loc[maint["EQP_TAG"].eq(CAL_TAG)].copy()
    parts = partchg.loc[partchg["WO_NO"].isin(events["WO_NO"])].copy()
    if parts.duplicated().any():
        raise ValueError("CAL01 부품교체에 정확히 같은 행이 중복됨")
    parts = parts.merge(part, on="PART_CD", how="left", validate="many_to_one", indicator=True)
    if not parts["_merge"].eq("both").all():
        raise ValueError("부품마스터에 없는 PART_CD가 있음")
    parts = parts.drop(columns="_merge")
    summary = parts.groupby("WO_NO", as_index=False).agg(
        PART_RECORD_COUNT=("PART_CD", "size"),
        PART_CODES=("PART_CD", lambda s: " | ".join(s.astype(str))),
        PART_NAMES=("PART_NM", lambda s: " | ".join(s.astype(str))),
        PART_QTY_TOTAL=("QTY", "sum"),
        PART_CHANGE_REASONS=("CHG_RSN", lambda s: " | ".join(s.astype(str))),
    )
    events = events.merge(summary, on="WO_NO", how="left", validate="one_to_one")
    events["HAS_PART_RECORD"] = events["PART_RECORD_COUNT"].notna()
    for column in ["PART_RECORD_COUNT", "PART_QTY_TOTAL"]:
        events[column] = events[column].fillna(0).astype(int)
    for column in ["PART_CODES", "PART_NAMES", "PART_CHANGE_REASONS"]:
        events[column] = events[column].fillna("")
    if not events["PART_CHG"].eq("Y").eq(events["HAS_PART_RECORD"]).all():
        raise ValueError("PART_CHG 표시와 실제 부품교체 유무가 다름")
    # 작업 기간과 기록된 정지 분량은 다른 값임. 정지 시작·종료를 역산하지 않음.
    events["WORK_MIN"] = (events["END_DT"] - events["STRT_DT"]).dt.total_seconds() / 60
    if events["WORK_MIN"].lt(0).any() or events["DOWN_MIN"].lt(0).any():
        raise ValueError("작업시간 또는 정지시간이 음수임")
    events["DOWN_RECORD_STATUS"] = "정지시간 미기록"
    events.loc[events["DOWN_MIN"].eq(0), "DOWN_RECORD_STATUS"] = "해당 정비의 정지시간 0 기록"
    events.loc[events["DOWN_MIN"].gt(0), "DOWN_RECORD_STATUS"] = "정지시간 기록 있음; 시점 미확정"
    events["DOWN_TO_WORK_RATIO"] = events["DOWN_MIN"].div(events["WORK_MIN"].where(events["WORK_MIN"].gt(0)))
    events["DOWN_EXCEEDS_WORK"] = events["DOWN_MIN"].astype("Float64").gt(events["WORK_MIN"].astype("Float64"))
    events["STOP_INTERVAL_KNOWN"] = False  # 현재 원본에는 실제 정지 시작·종료 컬럼이 없음.
    details = maint.loc[maint["EQP_TAG"].eq(CAL_TAG)].merge(
        parts, on="WO_NO", how="inner", validate="one_to_many"
    )
    return (
        events.sort_values(["DETC_DT", "WO_NO"]).reset_index(drop=True),
        details.sort_values(["STRT_DT", "WO_NO", "PART_CD"]).reset_index(drop=True),
    )


def apply_user_exclusions(temp):
    """사용자가 지정한 네 경계만 표시함. 원본의 행·순서·인덱스는 유지함."""
    annotated = temp.copy()
    annotated["EXCLUDED"] = False
    annotated["EXCLUSION_REASON"] = ""
    summary = []
    for lot, boundary, direction, reason in USER_EXCLUSIONS:
        boundary = pd.Timestamp(boundary)
        time_mask = annotated["MEAS_DT"].ge(boundary) if direction == "at_or_after" else annotated["MEAS_DT"].lt(boundary)
        hit = annotated["LOT_NO"].eq(lot) & time_mask
        annotated.loc[hit, "EXCLUDED"] = True
        annotated.loc[hit, "EXCLUSION_REASON"] = reason
        summary.append({"LOT_NO": lot, "boundary": boundary, "direction": direction,
                        "excluded_rows": int(hit.sum())})
    return annotated, pd.DataFrame(summary)
