"""전체 센서 후보와 정비 기록을 결합한 임시 약지도 라벨. 현장 정답 아님."""

import numpy as np
import pandas as pd


VERSION = "multisensor_domain_weak_v1_20261015"
AMPLITUDE_MULTIPLIER = 2.0
ASSOCIATION_HOURS = 24
CP_LOT_SIGMA_MULTIPLIER = 12.0
MIN_ELAPSED_SECONDS = 10
EQP_TAG = "P1-CR1-CAL01"
AMBIGUOUS_REMARK = r"원인\s*미상|확인\s*중|이상\s*없|재현\s*안|재점검\s*필요"


def build_weak_labels(raw_marked_with_grade, sustained_candidates, sources, maintenance):
    """(원본 순서 행 라벨, 후보별 판정표, 규칙·기여도 metadata)를 반환함.

    사용자 EXCLUDED 행만 NA임. 나머지 0은 규칙 미검출이며 정상 확정이 아님.
    1은 강한 지속 신호와 유효 정비 기록의 시간 연관을 동시에 만족한 행임.
    감지 전 24시간/작업 종료 후 24시간은 탐색 가정이며 고장 원인·회복 확인이 아님.
    원본 센서 컬럼을 수정하지 않으며, 반환 표는 X가 아닌 라벨/사후 근거 표임.
    """
    raw = raw_marked_with_grade
    required = {"LOT_NO", "MEAS_DT", "GRADE", "EXCLUDED"}
    if not required.issubset(raw.columns):
        raise ValueError(f"원본 표에 필요한 컬럼 없음: {sorted(required - set(raw.columns))}")
    if raw[list(required)].isna().any().any() or raw.duplicated(["LOT_NO", "MEAS_DT"]).any():
        raise ValueError("키·강종·제외 플래그가 비었거나 LOT/시각이 중복됨")
    if not raw.EXCLUDED.isin([True, False]).all():
        raise ValueError("EXCLUDED는 boolean이어야 함")
    sensor_columns = [c for c in raw if c.startswith(("TC-", "OP-")) and "_" not in c]
    sensor_columns += ["CLN-IN", "CP-Z4"]
    if len(sensor_columns) != 21 or not set(sensor_columns).issubset(raw.columns):
        raise ValueError("CP-Z4M을 제외한 원본 21계측이 필요함")
    n = len(raw)
    times = pd.to_datetime(raw.MEAS_DT, errors="raise").reset_index(drop=True)
    lot_values = raw.LOT_NO.to_numpy()
    excluded = raw.EXCLUDED.to_numpy(dtype=bool)
    output = raw[["LOT_NO", "MEAS_DT", "GRADE", "EXCLUDED"]].reset_index(drop=True).copy()
    output["LABEL"] = pd.Series(np.zeros(n, dtype=np.int8), dtype="Int8")
    output.loc[excluded, "LABEL"] = pd.NA
    output["LABEL_STATUS"] = "임시 약지도; 현장 확정 정답 아님"
    output.loc[excluded, "LABEL_STATUS"] = "사용자 지정 제외"
    output["LABEL_REASON"] = "전체 21계측 검토에서 이번 신호+정비 규칙 미검출; 정상 확정 아님"
    output.loc[excluded, "LABEL_REASON"] = "사용자 지정 시간 제외"
    if "EXCLUSION_REASON" in raw:
        output.loc[excluded, "LABEL_REASON"] = raw.EXCLUSION_REASON.to_numpy()[excluded]
    output["RULE"] = np.where(excluded, "user_excluded", "weak_rule_not_detected")
    for column in ["EVIDENCE_WO", "EVIDENCE_MNT_TYPE", "EVIDENCE_SENSOR", "EVIDENCE_CANDIDATE_IDS", "ASSOCIATION_KIND"]:
        output[column] = ""
    output["LABEL_VERSION"] = VERSION
    output["MODEL_INPUT_ALLOWED"] = False
    flags = {name: np.zeros(n, dtype=bool) for name in [
        "ANY_SENSOR_CANDIDATE", "CONTROL_RESPONSE_CONTEXT", "PERIODIC_CONTEXT",
        "LOT_BOUNDARY_CONTEXT", "MAINT_WORK_OVERLAP", "SCHEDULED_REPAIR_CONTEXT",
        "REPAIR_PREPOST_24H_CONTEXT", "GRADE_CHANGE_NEARBY_30MIN",
        "CP_RETURN_TO_BASELINE_CONTEXT",
    ]}

    # 전체 LOT의 수준 차이를 양성으로 만들지 않고 국소 지속 후보만 사용함.
    candidates = sustained_candidates.copy().reset_index(drop=True)
    candidate_required = {"CANDIDATE_ID", "LOT_NO", "GRADE", "SENSOR", "START", "END", "KIND", "AMPLITUDE", "THRESHOLD", "REVIEW_CATEGORY", "PERIODIC_CONTEXT", "LOT_BOUNDARY_CONTEXT"}
    if not candidate_required.issubset(candidates.columns):
        raise ValueError("전체 센서 지속 후보표의 필수 컬럼이 없음")
    if candidates.CANDIDATE_ID.isna().any() or candidates.CANDIDATE_ID.duplicated().any():
        raise ValueError("CANDIDATE_ID는 비어 있지 않은 고유값이어야 함")
    for column in ["START", "END"]:
        candidates[column] = pd.to_datetime(candidates[column], errors="raise")
    if candidates[["START", "END"]].isna().any().any() or candidates.START.gt(candidates.END).any():
        raise ValueError("후보 구간이 비었거나 역전됨")
    for column in ["PERIODIC_CONTEXT", "LOT_BOUNDARY_CONTEXT"]:
        if not candidates[column].isin([True, False]).all():
            raise ValueError(f"{column}은 boolean이어야 함")
    lot_indices = {}
    for lot in pd.unique(lot_values):
        idx = np.flatnonzero(lot_values == lot)
        idx = idx[np.argsort(times.iloc[idx].to_numpy())]
        lot_indices[lot] = idx
    time_array = times.to_numpy(dtype="datetime64[ns]")
    cp_reference = raw.loc[~excluded, ["LOT_NO", "CP-Z4"]].groupby("LOT_NO")["CP-Z4"]
    cp_centers = cp_reference.median()
    cp_sigmas = cp_reference.agg(lambda values: 1.4826 * (values - values.median()).abs().median())

    def positions(lot, start, end):
        idx = lot_indices.get(lot, np.array([], dtype=int))
        clock = time_array[idx]
        return idx[np.searchsorted(clock, np.datetime64(start), side="left"):
                   np.searchsorted(clock, np.datetime64(end), side="right")]

    # WO별 부품 집계를 유지하며 부품 상세행으로 증식된 입력은 거부함.
    maint_required = {"WO_NO", "EQP_TAG", "MNT_TYPE", "FAIL_MODE", "REMARK", "DETC_DT", "STRT_DT", "END_DT", "PART_CHANGE_REASONS", "HAS_PART_RECORD"}
    if not maint_required.issubset(maintenance.columns):
        raise ValueError("build_maintenance_context로 집계한 정비표가 필요함")
    maint = maintenance.loc[maintenance.EQP_TAG.eq(EQP_TAG)].copy()
    if maint.WO_NO.duplicated().any() or maint.WO_NO.isna().any():
        raise ValueError("정비는 WO당 한 행이어야 함")
    for column in ["DETC_DT", "STRT_DT", "END_DT"]:
        maint[column] = pd.to_datetime(maint[column], errors="raise")
    for column in ["MNT_TYPE", "FAIL_MODE", "REMARK", "PART_CHANGE_REASONS"]:
        maint[column] = maint[column].fillna("").astype(str).str.strip()
    ambiguous = maint.REMARK.str.contains(AMBIGUOUS_REMARK, regex=True)
    repair_fault = maint.MNT_TYPE.isin(["BM", "CBM"]) & maint.FAIL_MODE.isin(["ELE", "MAL", "WER"])
    damaged_part = maint.MNT_TYPE.eq("TBM") & maint.HAS_PART_RECORD.eq(True) & maint.PART_CHANGE_REASONS.str.contains("손상", regex=False)
    maint["WEAK_EVIDENCE_ELIGIBLE"] = (repair_fault | damaged_part) & ~ambiguous
    eligible = maint.loc[maint.WEAK_EVIDENCE_ELIGIBLE]
    for row in maint.itertuples(index=False):
        if pd.notna(row.STRT_DT) and pd.notna(row.END_DT):
            if row.END_DT < row.STRT_DT:
                raise ValueError("정비 작업시각 역전")
            flags["MAINT_WORK_OVERLAP"] |= (times.ge(row.STRT_DT) & times.lt(row.END_DT)).to_numpy()

    # 수리 날짜는 조업 맥락일 뿐 실제 정지시간이 아님. 날짜형 종료일은 그 날까지 포함함.
    calendar = sources["repair"].loc[sources["repair"].PLANT_CD.eq("CR1")]
    for row in calendar.itertuples(index=False):
        start = pd.Timestamp(row.STRT_DT).normalize()
        end = pd.Timestamp(row.END_DT).normalize() + pd.Timedelta(days=1)
        flags["SCHEDULED_REPAIR_CONTEXT"] |= (times.ge(start) & times.lt(end)).to_numpy()
        flags["REPAIR_PREPOST_24H_CONTEXT"] |= (
            (times.ge(start - pd.Timedelta(hours=24)) & times.lt(start)) |
            (times.ge(end) & times.lt(end + pd.Timedelta(hours=24)))
        ).to_numpy()
    events = sources["event"].loc[sources["event"].PLANT_CD.eq("CR1")]
    for stamp in pd.to_datetime(events.loc[events.EVT_TYPE.eq("강종변경"), "EVT_DT"]):
        flags["GRADE_CHANGE_NEARBY_30MIN"] |= times.between(stamp - pd.Timedelta(minutes=30), stamp + pd.Timedelta(minutes=30)).to_numpy()

    candidate_positions = {}
    for row in candidates.itertuples(index=False):
        idx = positions(row.LOT_NO, row.START, row.END)
        if len(idx) and not raw.GRADE.iloc[idx].eq(row.GRADE).all():
            raise ValueError("후보와 원본의 LOT 강종이 다름")
        candidate_positions[row.CANDIDATE_ID] = idx
        if row.SENSOR != "CP-Z4M":
            flags["ANY_SENSOR_CANDIDATE"][idx] = True
        if row.REVIEW_CATEGORY == "제어반응·운전조건 확인":
            flags["CONTROL_RESPONSE_CONTEXT"][idx] = True
        if row.PERIODIC_CONTEXT:
            flags["PERIODIC_CONTEXT"][idx] = True
        if row.LOT_BOUNDARY_CONTEXT:
            flags["LOT_BOUNDARY_CONTEXT"][idx] = True

    # OP 단독 변화는 양성으로 만들지 않고 같은 존 TC 지속 후보의 동시 관측을 요구함.
    companion_masks = {}
    for sensor in [c for c in sensor_columns if c.startswith("OP-")]:
        companion = sensor.replace("OP-", "TC-", 1)
        mask = np.zeros(n, dtype=bool)
        for row in candidates.loc[candidates.SENSOR.eq(companion)].itertuples(index=False):
            if pd.notna(row.AMPLITUDE) and pd.notna(row.THRESHOLD) and row.THRESHOLD > 0 and row.AMPLITUDE >= row.THRESHOLD:
                mask[candidate_positions[row.CANDIDATE_ID]] = True
        companion_masks[sensor] = mask

    def exact_runs(idx):
        if not len(idx):
            return []
        delta = np.diff(time_array[idx]).astype("timedelta64[ns]").astype("int64")
        cuts = np.flatnonzero(delta != 1_000_000_000) + 1
        return [part for part in np.split(idx, cuts) if len(part) >= MIN_ELAPSED_SECONDS + 1]

    contributions = []
    positive_evidence = {}
    decisions = []
    for row in candidates.itertuples(index=False):
        idx = candidate_positions[row.CANDIDATE_ID]
        reasons = []
        if row.SENSOR not in sensor_columns:
            reasons.append("auxiliary_sensor_not_used")
        if row.KIND not in ["local_deviation_low_10s", "local_deviation_high_10s"]:
            reasons.append("not_local_sustained_candidate")
        strong = pd.notna(row.AMPLITUDE) and pd.notna(row.THRESHOLD) and row.THRESHOLD > 0 and row.AMPLITUDE >= AMPLITUDE_MULTIPLIER * row.THRESHOLD
        if not strong:
            reasons.append("below_2x_candidate_amplitude")
        if row.PERIODIC_CONTEXT:
            reasons.append("periodic_context_not_positive")
        if row.LOT_BOUNDARY_CONTEXT or row.REVIEW_CATEGORY == "LOT 경계 운전조건 확인":
            reasons.append("lot_boundary_context_not_positive")
        if row.REVIEW_CATEGORY == "제어반응·운전조건 확인":
            reasons.append("TC_OP_control_response_not_positive")
        if row.REVIEW_CATEGORY not in ["이상 검토 우선", "LOT 경계 운전조건 확인", "제어반응·운전조건 확인", "보조계측·생성관계 확인"]:
            reasons.append("unknown_review_category")
        domain_records = []
        domain_mask = np.zeros(len(idx), dtype=bool)
        for event in eligible.itertuples(index=False):
            local_times = times.iloc[idx]
            pre = local_times.between(event.DETC_DT - pd.Timedelta(hours=ASSOCIATION_HOURS), event.DETC_DT).to_numpy() if pd.notna(event.DETC_DT) else np.zeros(len(idx), dtype=bool)
            post = local_times.between(event.END_DT, event.END_DT + pd.Timedelta(hours=ASSOCIATION_HOURS)).to_numpy() if pd.notna(event.END_DT) else np.zeros(len(idx), dtype=bool)
            if pre.any() or post.any():
                domain_mask |= pre | post
                domain_records.append((event, pre, post))
        if not domain_mask.any():
            reasons.append("no_eligible_maintenance_time_association")
        usable = ~excluded[idx] & ~flags["MAINT_WORK_OVERLAP"][idx] & ~flags["SCHEDULED_REPAIR_CONTEXT"][idx] & ~flags["REPAIR_PREPOST_24H_CONTEXT"][idx]
        cp_baseline_rejected = 0
        if row.SENSOR == "CP-Z4":
            # 과거5분 기준선의 지연으로 생기는 정상 수준 복귀 후보를 제외함.
            # CP에만 적용하며 동일 LOT 전체 관측으로 만든 사후 약지도 가정임.
            center = cp_centers.get(row.LOT_NO, np.nan)
            sigma = cp_sigmas.get(row.LOT_NO, np.nan)
            if not np.isfinite(center) or not np.isfinite(sigma) or sigma <= 0:
                far = np.zeros(len(idx), dtype=bool)
                reasons.append("CP_reference_scale_unavailable")
            else:
                residual = pd.to_numeric(raw["CP-Z4"].iloc[idx], errors="coerce").to_numpy(dtype=float) - center
                limit = CP_LOT_SIGMA_MULTIPLIER * sigma
                # 높은 CP가 내려오는 중에도 기준선 밖이면 이탈은 남아 있음.
                # 국소 기울기 부호가 아니라 현재 수준의 절대편차로 복귀를 구분함.
                far = np.abs(residual) > limit
            cp_baseline_rejected = int((~far & ~excluded[idx]).sum())
            flags["CP_RETURN_TO_BASELINE_CONTEXT"][idx[~far & ~excluded[idx]]] = True
            usable &= far
            if not far.any():
                reasons.append("CP_return_or_small_change_at_LOT_baseline")
        if row.SENSOR in raw:
            usable &= np.isfinite(pd.to_numeric(raw[row.SENSOR].iloc[idx], errors="coerce").to_numpy(dtype=float))
        if row.SENSOR in companion_masks:
            usable &= companion_masks[row.SENSOR][idx]
            companion = row.SENSOR.replace("OP-", "TC-", 1)
            usable &= np.isfinite(pd.to_numeric(raw[companion].iloc[idx], errors="coerce").to_numpy(dtype=float))
            if not companion_masks[row.SENSOR][idx].any():
                reasons.append("OP_without_same_zone_TC_candidate")
        runs = exact_runs(idx[usable & domain_mask]) if not reasons else []
        positive = np.concatenate(runs) if runs else np.array([], dtype=int)
        if not len(positive) and not reasons:
            reasons.append("context_or_gap_leaves_less_than_10s")
        used_wo, used_type, assoc_kinds = set(), set(), set()
        for event, pre, post in domain_records:
            event_positions = idx[pre | post]
            hit = np.intersect1d(positive, event_positions)
            if not len(hit):
                continue
            used_wo.add(event.WO_NO)
            used_type.add(event.MNT_TYPE)
            for kind, local_mask in [("pre_detection_24h", pre), ("post_work_end_24h", post)]:
                if np.intersect1d(hit, idx[local_mask]).size:
                    assoc_kinds.add(kind)
            for pos in hit:
                record = positive_evidence.setdefault(int(pos), {"wo": set(), "types": set(), "sensors": set(), "candidates": set(), "associations": set()})
                record["wo"].add(event.WO_NO)
                record["types"].add(event.MNT_TYPE)
                record["sensors"].add(row.SENSOR)
                record["candidates"].add(row.CANDIDATE_ID)
                if pd.notna(event.DETC_DT) and event.DETC_DT - pd.Timedelta(hours=ASSOCIATION_HOURS) <= times.iloc[pos] <= event.DETC_DT:
                    record["associations"].add("pre_detection_24h")
                if event.END_DT <= times.iloc[pos] <= event.END_DT + pd.Timedelta(hours=ASSOCIATION_HOURS):
                    record["associations"].add("post_work_end_24h")
            contributions.append({"LOT_NO": row.LOT_NO, "SENSOR": row.SENSOR, "MNT_TYPE": event.MNT_TYPE, "WO_NO": event.WO_NO, "POSITIONS": hit.tolist()})
        record = row._asdict()
        record.update({
            "WEAK_DECISION": "temporary_positive" if len(positive) else "not_positive_under_this_rule",
            "DECISION_CODES": "signal_and_eligible_record_time_association" if len(positive) else " | ".join(reasons),
            "SIGNAL_AMPLITUDE_RATIO": float(row.AMPLITUDE / row.THRESHOLD) if pd.notna(row.THRESHOLD) and row.THRESHOLD > 0 else None,
            "MATCHED_POSITIVE_ROWS": len(positive), "EXCLUDED_ROWS": int(excluded[idx].sum()),
            "WORK_OVERLAP_ROWS": int(flags["MAINT_WORK_OVERLAP"][idx].sum()),
            "REPAIR_CONTEXT_ROWS": int((flags["SCHEDULED_REPAIR_CONTEXT"][idx] | flags["REPAIR_PREPOST_24H_CONTEXT"][idx]).sum()),
            "CP_BASELINE_REJECTED_ROWS": cp_baseline_rejected,
            "CP_LOT_MEDIAN": float(cp_centers.get(row.LOT_NO, np.nan)) if row.SENSOR == "CP-Z4" else None,
            "CP_LOT_MAD_SIGMA": float(cp_sigmas.get(row.LOT_NO, np.nan)) if row.SENSOR == "CP-Z4" else None,
            "EVIDENCE_WO": " | ".join(sorted(used_wo)), "EVIDENCE_MNT_TYPE": " | ".join(sorted(used_type)),
            "ASSOCIATION_KIND": " | ".join(sorted(assoc_kinds)),
            "ELIGIBLE_CONTEXT_WO": " | ".join(event.WO_NO for event, _, _ in domain_records),
            "POSITIVE_RUNS": " | ".join(f"{times.iloc[run[0]].isoformat()}~{times.iloc[run[-1]].isoformat()}" for run in runs),
            "LABEL_STATUS": "임시 약지도; 센서·존 고장 원인 확정 아님", "MODEL_INPUT_ALLOWED": False,
        })
        decisions.append(record)

    for pos, evidence in positive_evidence.items():
        output.at[pos, "LABEL"] = 1
        output.at[pos, "RULE"] = "strong_local_signal_AND_maintenance_time_association"
        output.at[pos, "LABEL_REASON"] = "강한 국소 신호 10초 이상과 유효 정비의 24시간 시간연관 동시 충족; 해당 센서 고장 원인 확정 아님"
        for column, key in [("EVIDENCE_WO", "wo"), ("EVIDENCE_MNT_TYPE", "types"), ("EVIDENCE_SENSOR", "sensors"), ("EVIDENCE_CANDIDATE_IDS", "candidates"), ("ASSOCIATION_KIND", "associations")]:
            output.at[pos, column] = " | ".join(sorted(evidence[key]))
    for key, values in flags.items():
        output[key] = values
    output["EVIDENCE_CONFIDENCE"] = np.where(output.LABEL.eq(1).fillna(False), "임시 시간연관; 원인 미확정", "규칙 미검출 또는 사용자 제외; 정상 확정 아님")

    def contribution_counts(keys):
        groups = {}
        for record in contributions:
            group = tuple(record[key] for key in keys)
            groups.setdefault(group, set()).update(record["POSITIONS"])
        return [{**dict(zip(keys, group)), "POSITIVE_ROWS": len(pos)} for group, pos in sorted(groups.items())]

    metadata = {
        "version": VERSION, "label_status": "사용자 선택한 첫 실험용 임시 약지도; 현장 정답 아님",
        "source_rows": n, "excluded_rows": int(excluded.sum()), "retained_rows": int((~excluded).sum()),
        "positive_rows": int(output.LABEL.eq(1).sum()), "negative_rows": int(output.LABEL.eq(0).sum()),
        "zero_definition": "21계측 신호+유효 정비 시간연관 규칙 미검출; 불확실 후보·운전 맥락도 포함하므로 정상 확정이 아님",
        "one_definition": "강한 국소 지속 신호와 적격 정비의 감지 전/작업 종료 후 시간연관 AND; 센서 고장 원인 확정이 아님",
        "candidate_count": len(candidates), "sensor_columns_reviewed": sensor_columns,
        "sensor_candidate_counts": {sensor: int(candidates.SENSOR.eq(sensor).sum()) for sensor in sensor_columns},
        "periodic_context_true_candidates": int(candidates.PERIODIC_CONTEXT.sum()),
        "amplitude_multiplier": AMPLITUDE_MULTIPLIER, "association_hours": ASSOCIATION_HOURS,
        "cp_lot_sigma_multiplier": CP_LOT_SIGMA_MULTIPLIER,
        "cp_baseline_rule": "CP만 사용자 제외 후 동일 LOT 중앙값과 현재값의 절대편차가 12×1.4826×MAD를 넘는 실제 행을 요구하고 다시 1초간격10초 지속 확인. 5분 기준선 지연에 따른 기준선 복귀 후보를 1로 만들지 않음. 국소 감소 중이어도 현재 수준이 기준선에서 멀면 이탈로 남음",
        "cp_reference_by_lot": [{"LOT_NO": int(lot), "MEDIAN": float(cp_centers.loc[lot]), "MAD_SIGMA": float(cp_sigmas.loc[lot])} for lot in cp_centers.index],
        "min_elapsed_seconds": MIN_ELAPSED_SECONDS, "min_observations": MIN_ELAPSED_SECONDS + 1,
        "threshold_status": "2배 문턱·CP12MADσ·24시간·수리전후24시간은 탐색 가정이며 공정허용치가 아님. 행수 목표 없음",
        "maintenance_eligible_count": len(eligible), "maintenance_eligible_wo": eligible.WO_NO.tolist(),
        "maintenance_rule": "BM/CBM의 ELE·MAL·WER 또는 TBM 손상교체; 원인미상·확인중·이상없음·재현안됨·재점검필요 제외",
        "positive_contribution_by_lot": contribution_counts(["LOT_NO"]),
        "positive_contribution_by_type": contribution_counts(["MNT_TYPE"]),
        "positive_contribution_by_sensor": contribution_counts(["SENSOR"]),
        "positive_contribution_by_lot_type_sensor": contribution_counts(["LOT_NO", "MNT_TYPE", "SENSOR"]),
        "contribution_note": "각 그룹 내부는 고유 행 수. 여러 센서/WO 근거가 겹치면 그룹 합계는 전체 양성 수와 다를 수 있음",
        "event_types": {str(k): int(v) for k, v in events.EVT_TYPE.value_counts().items()},
        "limitations": [
            "정비는 CAL01 설비 단위이며 특정 존·센서 귀속이 없음. 근접 기록은 인과 근거가 아님",
            "모든 21계측을 검토하지만 후보가 없는 센서가 정상으로 검증됐다는 뜻은 아님. CP-Z4M은 의미 미확인 보조계측으로 제외",
            "CP도 단독 신호로 1이 되지 않고 적격 정비 근거가 필요함. OP는 같은 존 TC 지속 후보와 동시 10초 관측을 추가 요구",
            "TC-Z3/OP-Z3 제어반응 분류·LOT경계·주기 후보·작업 중·수리일정/전후24시간은 양성으로 채택하지 않음. 사용자 제외가 아니므로 이 행들은 규칙 미검출 0",
            "수리 종료 날짜는 날짜 포함으로 처리했지만 실제 정지구간이 아님. DOWN_MIN으로 정지시점을 역산하지 않음",
            "신호 2배 조건은 후보 최대이탈의 강도임. 채택한 각 행이 2배 문턱을 넘는다는 뜻은 아님",
            "후보 생성의 LOT 통계·사후 정비 시각은 미래정보일 수 있음. 모든 근거·판정·문맥 플래그는 X에서 제외",
            "CP 기준선은 강종 내 동일 LOT의 전체 유효 관측을 사용한 사후 약지도이며 운전단계 혼합에 오염될 수 있음. 현장 정상 분포나 실시간 기준선으로 보증하지 않음. TC 등 다른 센서에 12MAD 조건을 일괄 적용하지 않음",
            "전체 LOT 수준 차이는 양성 규칙으로 사용하지 않음. 라벨 0에 남은 미해결 사례도 존재함",
        ],
        "model_input_forbidden": [c for c in output.columns if c not in ["LOT_NO", "MEAS_DT", "GRADE", "LABEL"]],
    }
    assert len(output) == n and output.loc[~excluded, "LABEL"].notna().all()
    assert output.loc[excluded, "LABEL"].isna().all()
    assert not (output.LABEL.eq(1).fillna(False).to_numpy() & (excluded | flags["MAINT_WORK_OVERLAP"] | flags["SCHEDULED_REPAIR_CONTEXT"] | flags["REPAIR_PREPOST_24H_CONTEXT"])).any()
    return output, pd.DataFrame(decisions), metadata
