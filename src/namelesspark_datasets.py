"""하나의 원본 행 기준표에서 분류·회귀 입력을 구성함."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from namelesspark_pipeline import apply_user_exclusions, build_lot_context, build_maintenance_context

DATASET_VERSION = "v1"
KEYS = ["LOT_NO", "MEAS_DT"]
TARGET_SENSORS = ["TC-Z3", "OP-Z3", "TC-Z4", "OP-Z4", "TC-Z5", "OP-Z5", "CP-Z4"]
PAST_SUFFIXES = ["1분전", "5분전", "직전10분평균", "직전10분표준편차", "직전두분차이"]
PAST_FEATURES = [f"{sensor}_{suffix}" for sensor in TARGET_SENSORS for suffix in PAST_SUFFIXES]
PAST_FEATURES += [f"{sensor}_직전10분포화율" for sensor in ["OP-Z3", "OP-Z4", "OP-Z5"]]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_master(sources, features, row_labels, row_links):
    """원본 1행당 1행. 사용자 제외 행도 남기되 LABEL과 입력 유효성을 분리함."""
    raw = sources["temp"]
    marked, _ = apply_user_exclusions(raw)
    lots = build_lot_context(raw, sources["event"])
    master = marked.merge(lots[["LOT_NO", "GRADE", "START"]], on="LOT_NO", validate="many_to_one")
    master["LOT_ELAPSED_MIN"] = (master.MEAS_DT - master.START).dt.total_seconds() / 60
    master = master.drop(columns="START")
    master["FEATURE_MINUTE"] = master.MEAS_DT.dt.floor("min")
    if features.duplicated(KEYS).any():
        raise ValueError("1분 파생표의 LOT·시각 키가 중복됨")
    past = features[[*KEYS, "강종", *PAST_FEATURES]].rename(
        columns={"MEAS_DT": "FEATURE_MINUTE", "강종": "FEATURE_GRADE"})
    master = master.merge(past, on=["LOT_NO", "FEATURE_MINUTE"], how="left", validate="many_to_one")
    if not master.loc[~master.EXCLUDED, "GRADE"].eq(master.loc[~master.EXCLUDED, "FEATURE_GRADE"]).all():
        raise ValueError("06 파생표의 시각·강종이 현재 제외 조건과 일치하지 않음")
    master.loc[master.EXCLUDED, PAST_FEATURES] = np.nan
    master = master.drop(columns="FEATURE_GRADE")
    if row_labels.duplicated(KEYS).any() or len(row_labels) != len(raw):
        raise ValueError("행별 라벨은 원본 고유 키를 한 번씩 포함해야 함")
    metadata_columns = [c for c in row_labels if c not in master.columns and c not in KEYS]
    if "LABEL" not in metadata_columns:
        raise ValueError("행별 LABEL이 없음")
    master = master.merge(row_labels[KEYS + metadata_columns], on=KEYS, how="left", validate="one_to_one", indicator=True)
    if not master._merge.eq("both").all():
        raise ValueError("라벨표와 원본의 행 키가 다름")
    master = master.drop(columns="_merge")
    master = master.rename(columns={"MODEL_INPUT_ALLOWED": "EVIDENCE_INPUT_ALLOWED"})
    # 라벨 근거 WO에 연결된 정비·교체 값을 남김. 여러 부품 때문에 센서 행이 늘지 않게 함.
    maintenance, _ = build_maintenance_context(sources["maint"], sources["partchg"], sources["part"])
    event_index = maintenance.set_index("WO_NO")
    for field in ["DOWN_MIN", "HAS_PART_RECORD", "PART_NAMES", "PART_QTY_TOTAL", "PART_CHANGE_REASONS", "FAIL_MODE"]:
        summaries = {}
        for value in master.EVIDENCE_WO.fillna("").unique():
            events = value.split(" | ") if value else []
            summaries[value] = " | ".join(f"{wo}:{event_index.at[wo, field]}" for wo in events)
        master[f"EVIDENCE_{field}"] = master.EVIDENCE_WO.fillna("").map(summaries)
    if master.loc[~master.EXCLUDED, "LABEL"].isna().any():
        raise ValueError("이번 실험의 비제외 행에는 임시 0·1이 필요함")
    if not master.loc[~master.EXCLUDED, "LABEL"].isin([0, 1]).all():
        raise ValueError("LABEL은 0·1이어야 함")
    master.loc[master.EXCLUDED, "LABEL"] = pd.NA
    master["LABEL"] = master.LABEL.astype("Int8")
    links = row_links[KEYS + ["LOT_CONTEXT_ID", "SENSOR_CANDIDATE_IDS"]]
    master = master.merge(links, on=KEYS, how="left", validate="one_to_one")
    if master.loc[~master.EXCLUDED, "LOT_CONTEXT_ID"].isna().any():
        raise ValueError("비제외 행의 도메인 근거 연결이 누락됨")
    for column in ["LOT_CONTEXT_ID", "SENSOR_CANDIDATE_IDS"]:
        master[column] = master[column].fillna("")
    sensors = [c for c in raw if c not in KEYS and c != "CP-Z4M"]
    input_columns = [*sensors, "LOT_ELAPSED_MIN", *PAST_FEATURES]
    for grade in sorted(lots.GRADE.unique()):
        column = f"GRADE_{grade}"
        master[column] = master.GRADE.eq(grade).astype("int8")
        input_columns.append(column)
    master["FEATURES_COMPLETE"] = np.isfinite(master[input_columns].to_numpy(dtype=float)).all(axis=1)
    master["MODEL_ELIGIBLE"] = ~master.EXCLUDED & master.FEATURES_COMPLETE & master.LABEL.notna()
    master = master.sort_values(KEYS).reset_index(drop=True)
    master.insert(0, "ROW_ID", master.LOT_NO.astype(str) + "_" + master.MEAS_DT.dt.strftime("%Y%m%dT%H%M%S"))
    master = master[[c for c in master if c != "LABEL"] + ["LABEL"]]
    pd.testing.assert_frame_equal(master[raw.columns], raw.sort_values(KEYS).reset_index(drop=True))
    assert len(master) == len(raw) and master.ROW_ID.is_unique
    assert not set(["LABEL", "EXCLUDED", "LABEL_REASON", "ROW_ID", *KEYS]).intersection(input_columns)
    return master, input_columns


def export_master(root, master, input_columns, label_metadata, source_files):
    """기준 CSV는 하나만 저장하고 분류·회귀는 같은 표를 참조하는 정의 파일을 둠."""
    root = Path(root)
    processed = root / "data/processed"
    master_path = processed / f"cal01_base_{DATASET_VERSION}.csv"
    meta_dir = processed / "metadata" / DATASET_VERSION
    meta_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_version": DATASET_VERSION,
        "master_file": master_path.name,
        "row_key": ["ROW_ID", *KEYS],
        "rows": len(master), "columns": len(master.columns),
        "label_0": int(master.LABEL.eq(0).sum()), "label_1": int(master.LABEL.eq(1).sum()),
        "excluded_rows": int(master.EXCLUDED.sum()), "label_na": int(master.LABEL.isna().sum()),
        "model_eligible_rows": int(master.MODEL_ELIGIBLE.sum()),
        "eligible_label_counts": {str(int(k)): int(v) for k, v in master.loc[master.MODEL_ELIGIBLE, "LABEL"].value_counts().items()},
        "input_columns": input_columns,
        "raw_measurement_columns": [c for c in master if c.startswith(("TC-", "OP-")) and "_" not in c] + ["CLN-IN", "CP-Z4", "CP-Z4M"],
        "label_policy": label_metadata,
        "input_semantics": "현재 관측과 현재 분 이전에 완성된 과거 특징만 사용. LABEL·근거·사후 사건은 X에서 제외함.",
        "split_status": "not_assigned", "sampling_applied": False, "models_trained": False,
        "sampling_policy": "시간·LOT로 먼저 분할하고 학습 부분에만 정상:이상=9:1 적용. 검증·시험은 원래 분포 유지.",
        "source_sha256": {str(Path(p).relative_to(root)).replace('\\', '/'): sha256(p) for p in source_files},
    }
    # 같은 버전에서 입력이나 규칙이 달라지면 기존 기준표를 덮어쓰지 않음.
    manifest_path = meta_dir / "dataset.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ["source_sha256", "label_policy", "input_columns"]:
            if previous.get(key) != manifest[key]:
                raise ValueError("입력 또는 라벨 규칙이 달라졌으므로 새 DATASET_VERSION이 필요함")
    master.to_csv(master_path, index=False, encoding="utf-8-sig")
    manifest["master_sha256"] = sha256(master_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for task in ["classification", "regression"]:
        directory = processed / task / DATASET_VERSION
        directory.mkdir(parents=True, exist_ok=True)
        contract = {
            "dataset_version": DATASET_VERSION, "master_relative_path": "../../" + master_path.name,
            "master_sha256": manifest["master_sha256"], "input_columns": input_columns,
            "row_filter": "MODEL_ELIGIBLE == True", "split_status": "not_assigned", "sampling_applied": False,
        }
        if task == "classification":
            contract.update(target="LABEL", label_kind="weak_domain_assisted_not_ground_truth",
                            methods=["Z-score", "IsolationForest", "RandomForestClassifier"],
                            evaluation="같은 평가 행과 LABEL로 비교함. Z-score와 IF의 fit에는 LABEL을 전달하지 않음.")
        else:
            contract.update(target_sensor=None, horizon_seconds=None, status="target_not_selected",
                            target_rule="같은 LOT의 정확한 미래 시각을 연결. 미래값은 X에서 제외하며 사용자 제외·분할 경계를 넘는 정답은 사용하지 않음.")
        (directory / "dataset.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return master_path, manifest


def classification_inputs(master, input_columns):
    """세 방법에서 공통 평가 행을 사용할 수 있게 동일한 행을 반환함."""
    chosen = master.loc[master.MODEL_ELIGIBLE].copy()
    return chosen[input_columns], chosen.LABEL.astype("int8"), chosen[["ROW_ID", *KEYS, "GRADE"]]


def regression_inputs(master, input_columns, target_sensor, horizon_seconds, split_by_row=None):
    """예측 대상을 정했을 때만, 같은 LOT의 실제 미래 관측을 정답으로 연결함."""
    if target_sensor not in master or target_sensor not in input_columns or "_" in target_sensor or target_sensor == "LOT_ELAPSED_MIN":
        raise ValueError("원본 센서 중 명시적인 예측 대상이 필요함")
    if horizon_seconds <= 0:
        raise ValueError("미래 예측 시차는 양수 초 단위여야 함")
    frame = master.loc[master.MODEL_ELIGIBLE, ["ROW_ID", *KEYS, *input_columns]].copy()
    frame["TARGET_DT"] = frame.MEAS_DT + pd.Timedelta(seconds=horizon_seconds)
    future = master.loc[~master.EXCLUDED, ["ROW_ID", *KEYS, target_sensor]].rename(
        columns={"ROW_ID": "TARGET_ROW_ID", "MEAS_DT": "TARGET_DT", target_sensor: "TARGET"})
    frame = frame.merge(future, on=["LOT_NO", "TARGET_DT"], how="left", validate="many_to_one")
    frame = frame.loc[np.isfinite(pd.to_numeric(frame.TARGET, errors="coerce"))].copy()
    if split_by_row is not None:
        start_split = frame.ROW_ID.map(split_by_row)
        target_split = frame.TARGET_ROW_ID.map(split_by_row)
        frame = frame.loc[start_split.notna() & start_split.eq(target_split)].copy()
    return frame
