"""저장된 v7 데이터와 예측 파일로 보고서 사례 그림 4개를 만든다."""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=os.path.join(ROOT, "figures", "namelesspark", "report"))
    args = parser.parse_args()

    R = os.path.join(ROOT, "data", "processed", "model_results")
    T = "_common_roll10_zpast_opcommon_furnace_control"
    FIG = os.path.abspath(args.output_dir)
    os.makedirs(FIG, exist_ok=True)
    df = pd.read_csv(os.path.join(ROOT, "data", "processed", "cal01_base_v7.csv"), parse_dates=["MEAS_DT"])
    df = df[df["EXCLUDED"] == False].sort_values(["LOT_NO", "MEAS_DT"]).reset_index(drop=True)
    df = df.copy()
    pred = {}
    for z in ["Z3", "Z4"]:
        pred[z] = pd.read_csv(os.path.join(R, "cal01_base_v7_%s%s_predictions.csv" % (z, T)), parse_dates=["MEAS_DT"])


    def past_z(frame, sensor):
        out = pd.Series(0.0, index=frame.index)
        for lot, g in frame.groupby("LOT_NO"):
            v = g[sensor]
            prev = v.shift(1)
            pm = prev.expanding(min_periods=30).mean()
            ps = prev.expanding(min_periods=30).std(ddof=0).replace(0, np.nan)
            out[g.index] = ((v - pm).abs() / ps).fillna(0).values
        return out


    for s in ["TC-Z3", "OP-Z3", "TC-Z4", "OP-Z4", "CP-Z4"]:
        df[s + "__ZP"] = past_z(df, s)


    def window(lot, start, end, zone):
        d = df[(df["LOT_NO"] == lot) & (df["MEAS_DT"] >= start) & (df["MEAS_DT"] <= end)].copy()
        if zone in pred:
            d = d.merge(pred[zone][["LOT_NO", "MEAS_DT", "LABEL", "PRED_Z", "PRED_IF", "PRED_RF"]], on=["LOT_NO", "MEAS_DT"], how="left")
        return d


    def draw(d, sensors, units, title, shade, fname, note):
        fig, axes = plt.subplots(len(sensors) + 1, 1, figsize=(9, 1.75 * len(sensors) + 1.35), sharex=True,
                                 gridspec_kw={"height_ratios": [3] * len(sensors) + [1.2]})
        for ax, s, u in zip(axes[:-1], sensors, units):
            ax.plot(d["MEAS_DT"], d[s], color="#05507D", lw=1.4)
            ax.fill_between(d["MEAS_DT"], d[s + "__MIN"], d[s + "__MAX"], color="#05507D", alpha=0.12, lw=0)
            for (a, b, lab, col) in shade:
                ax.axvspan(a, b, color=col, alpha=0.18, lw=0)
            ax.set_ylabel("%s [%s]" % (s, u))
            ax.grid(alpha=0.25)
        ax = axes[-1]
        y = 0
        for key, name, col in [("LABEL", "정답", "#4B5151"), ("PRED_Z", "Z-score", "#9BAFBA"), ("PRED_IF", "IsolationForest", "#00A5E5"), ("PRED_RF", "RandomForest", "#84754E")]:
            if key in d:
                m = d[key] == 1
                ax.scatter(d.loc[m, "MEAS_DT"], [y] * int(m.sum()), marker="s", s=28, color=col)
            y = y + 1
        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels(["정답 1", "Z-score 1", "IF 1", "RF 1"])
        ax.set_ylim(-0.6, 3.6)
        ax.set_xlabel("시각 (1분 평균)")
        ax.grid(alpha=0.25, axis="x")
        for (a, b, lab, col) in shade:
            ax.axvspan(a, b, color=col, alpha=0.18, lw=0)
        fig.suptitle(title, fontsize=11, fontweight="bold")
        fig.text(0.01, 0.005, note, fontsize=7.5, color="#4B5151")
        fig.tight_layout(rect=[0, 0.03, 1, 0.97])
        fig.savefig(os.path.join(FIG, fname), dpi=160)
        plt.close(fig)
        print("saved", fname)


    # 사례 1 (미탐): T08 LOT 069 TC-Z3 07-07 23:00~23:15
    d = window(240069, "2024-07-07 22:35", "2024-07-07 23:40", "Z3")
    w = d[(d["MEAS_DT"] >= "2024-07-07 23:00") & (d["MEAS_DT"] <= "2024-07-07 23:15")]
    print("T08 창:", len(w), "분 / 정답1", int(w["LABEL"].sum()), "/ Z", int(w["PRED_Z"].sum()), "IF", int(w["PRED_IF"].sum()), "RF", int(w["PRED_RF"].sum()))
    print("  TC-Z3 %.1f~%.1f, OP-Z3 %.1f~%.1f, 지난값Z 최대 TC %.2f OP %.2f" % (w["TC-Z3"].min(), w["TC-Z3"].max(), w["OP-Z3"].min(), w["OP-Z3"].max(), w["TC-Z3__ZP"].max(), w["OP-Z3__ZP"].max()))
    lot = df[df["LOT_NO"] == 240069]
    print("  LOT 069 TC-Z3 평균 %.1f 표준편차 %.2f" % (lot["TC-Z3"].mean(), lot["TC-Z3"].std()))
    draw(d, ["TC-Z3", "OP-Z3"], ["℃", "%"], "미탐 사례 1: LOT 240069 (SPHC) TC-Z3, 2024-07-07 23:00~23:15 (팀 판단 T08 = 이상 1)",
         [(pd.Timestamp("2024-07-07 23:00"), pd.Timestamp("2024-07-07 23:15:59"), "T08", "#BF3D50")], "01_미탐_T08_069_TC-Z3.png",
         "자료: data/processed/cal01_base_v7.csv, model_results/cal01_base_v7_Z3_*_predictions.csv (v6 최종 입력, 시간순 걷기). 음영 = 팀 판단 T08. 띠 = 1분 안 최소~최대")

    # 사례 2 (미탐): LOT 069 CP-Z4 짧은 튐 T02~T07
    d = window(240069, "2024-07-07 18:50", "2024-07-07 19:50", "Z4")
    for tid, a, b in [("T02", "18:59", "19:02"), ("T03", "19:07", "19:09"), ("T04", "19:11", "19:12"), ("T05", "19:21", "19:22"), ("T06", "19:38", "19:39"), ("T07", "19:41", "19:42")]:
        w = d[(d["MEAS_DT"] >= "2024-07-07 " + a) & (d["MEAS_DT"] <= "2024-07-07 " + b + ":59")]
        print("%s %s~%s: 분 %d, 정답1 %d, Z %d, IF %d, RF %d, CP 최대 %.3f, 지난값Z 최대 %.1f" % (tid, a, b, len(w), int(w["LABEL"].sum()), int(w["PRED_Z"].sum()), int(w["PRED_IF"].sum()), int(w["PRED_RF"].sum()), w["CP-Z4__MAX"].max(), w["CP-Z4__ZP"].max()))
    shade = []
    for a, b in [("18:59", "19:02"), ("19:07", "19:09"), ("19:11", "19:12"), ("19:21", "19:22"), ("19:38", "19:39"), ("19:41", "19:42")]:
        shade.append((pd.Timestamp("2024-07-07 " + a), pd.Timestamp("2024-07-07 " + b + ":59"), "T", "#BF3D50"))
    draw(d, ["CP-Z4", "TC-Z4"], ["-", "℃"], "미탐 사례 2: LOT 240069 CP-Z4, 2024-07-07 18:59~19:42 짧은 튐 6건 (팀 판단 T02~T07 = 이상 1)",
         shade, "02_미탐_T02-T07_069_CP-Z4.png",
         "자료: cal01_base_v7.csv, cal01_base_v7_Z4_*_predictions.csv. 음영 = 팀 판단 구간 (정수진 추천, 팀 미확정 포함). 띠 = 1분 안 최소~최대")

    # 사례 3 (오탐): LOT 108 Z4 RF 헛경보 묶음
    p = pred["Z4"]
    q = p[p["LOT_NO"] == 240108].sort_values("MEAS_DT").reset_index(drop=True)
    fp = (q["LABEL"] == 0) & (q["PRED_RF"] == 1)
    runs = []
    i = 0
    while i < len(q):
        if fp[i]:
            j = i
            while j + 1 < len(q) and fp[j + 1]:
                j = j + 1
            runs.append((q.loc[i, "MEAS_DT"], q.loc[j, "MEAS_DT"], j - i + 1))
            i = j + 1
        else:
            i = i + 1
    runs.sort(key=lambda r: -r[2])
    print("LOT 108 Z4 RF 헛경보 묶음 (긴 순):", [(str(a)[5:16], n) for a, b, n in runs[:6]], "/ 전체", int(fp.sum()), "분")
    a, b, n = runs[0]
    d = window(240108, a - pd.Timedelta(minutes=25), b + pd.Timedelta(minutes=25), "Z4")
    w = d[(d["MEAS_DT"] >= a) & (d["MEAS_DT"] <= b)]
    print("  가장 긴 묶음 %s~%s %d분: TC-Z4 %.1f~%.1f, OP-Z4 %.1f~%.1f, CP %.3f~%.3f, 지난값Z 최대 TC %.1f OP %.1f CP %.1f, Z-score 1 %d분, IF 1 %d분" % (
        str(a)[5:16], str(b)[11:16], n, w["TC-Z4"].min(), w["TC-Z4"].max(), w["OP-Z4"].min(), w["OP-Z4"].max(), w["CP-Z4"].min(), w["CP-Z4"].max(),
        w["TC-Z4__ZP"].max(), w["OP-Z4__ZP"].max(), w["CP-Z4__ZP"].max(), int(w["PRED_Z"].sum()), int(w["PRED_IF"].sum())))
    lot = df[df["LOT_NO"] == 240108]
    print("  LOT 108 TC-Z4 평균 %.1f 표준편차 %.2f, OP-Z4 평균 %.1f 표준편차 %.2f, CP 평균 %.3f 표준편차 %.4f" % (lot["TC-Z4"].mean(), lot["TC-Z4"].std(), lot["OP-Z4"].mean(), lot["OP-Z4"].std(), lot["CP-Z4"].mean(), lot["CP-Z4"].std()))
    draw(d, ["TC-Z4", "OP-Z4", "CP-Z4"], ["℃", "%", "-"], "오탐 사례 1: LOT 240108 (SPFH590) Z4, %s~%s RandomForest 경보 %d분 (검토 라벨 0)" % (str(a)[5:16], str(b)[11:16], n),
         [(a, b + pd.Timedelta(seconds=59), "RF", "#84754E")], "03_오탐_108_Z4_RF.png",
         "자료: cal01_base_v7.csv, cal01_base_v7_Z4_*_predictions.csv. 음영 = RandomForest가 1이라 한 묶음. 띠 = 1분 안 최소~최대")

    # 사례 4 (오탐, 2단계): LOT 024 CP-Z4 J007, J013 03-08 04:55~05:01
    d = window(240024, "2024-03-08 04:35", "2024-03-08 05:25", "none")
    w = d[(d["MEAS_DT"] >= "2024-03-08 04:55") & (d["MEAS_DT"] <= "2024-03-08 05:01")]
    print("J007 창: CP %.3f~%.3f (LOT 평균 %.3f), CP 지난값Z 최대 %.1f, TC-Z3 %.1f→%.1f (변화 %.1f℃), TC-Z4 %.1f~%.1f" % (
        w["CP-Z4"].min(), w["CP-Z4"].max(), df[df["LOT_NO"] == 240024]["CP-Z4"].mean(), w["CP-Z4__ZP"].max(), w["TC-Z3"].iloc[0], w["TC-Z3"].iloc[-1], w["TC-Z3"].max() - w["TC-Z3"].min(), w["TC-Z4"].min(), w["TC-Z4"].max()))
    draw(d, ["CP-Z4", "TC-Z3", "TC-Z4"], ["-", "℃", "℃"], "오탐 사례 2 (후보 단위): LOT 240024 (SPFH590) CP-Z4, 2024-03-08 04:55~05:01 (팀 판단 J007, J013 = 공통 움직임 0)",
         [(pd.Timestamp("2024-03-08 04:55"), pd.Timestamp("2024-03-08 05:01:59"), "J", "#00A5E5")], "04_오탐_024_CP-Z4_J007.png",
         "자료: cal01_base_v7.csv, 14번 노트북 후보 단위 RF (LOT 하나 빼고 학습) 확률 0.81. 음영 = 검토 표 J007, J013. LOT 024는 03 시간순 걷기의 학습 전용 LOT")


if __name__ == "__main__":
    main()
