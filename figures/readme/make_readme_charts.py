"""README용 결과 그림 (matplotlib, 다크·라이트 두 벌)

실행 (저장소 루트에서, 03 결과 파일이 data/processed/model_results에 있어야 함):
    python figures/readme/make_readme_charts.py

- lot_f1: 시험 LOT별 F1 (정답 1이 있는 구역의 평균), 세 모델
- heatmap: 구역 × 시험 LOT RandomForest F1 (정답 1이 없는 칸은 빈칸)
- zone_f1: 구역별 합산 F1, 세 모델
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RESULT_DIR = os.path.join(ROOT, "data", "processed", "model_results")
DATA_FILE = "cal01_base_v7"
TAIL = "_common_roll10_zpast_opcommon_furnace_control"
ZONES = ["CLN", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
MODELS = [("Z-score (지난 값)", "Z-score", "#5ec8ff"), ("IsolationForest", "IsolationForest", "#ffb347"), ("RandomForest", "RandomForest", "#a8ff3e")]
MODELS_LIGHT = {"#5ec8ff": "#1f7fb8", "#ffb347": "#e07b00", "#a8ff3e": "#3f8f1a"}

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def theme_colors(theme):
    if theme == "dark":
        return {"bg": "#0b0f0c", "ink": "#e9f2e8", "sub": "#9fb39d", "grid": "#22312a"}
    return {"bg": "#ffffff", "ink": "#15201a", "sub": "#5a6b5c", "grid": "#e1e8df"}


def model_color(color, theme):
    return color if theme == "dark" else MODELS_LIGHT[color]


def style(ax, t):
    ax.set_facecolor(t["bg"])
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(t["grid"])
    ax.tick_params(colors=t["sub"], labelsize=11)
    ax.yaxis.label.set_color(t["sub"])
    ax.xaxis.label.set_color(t["sub"])
    ax.title.set_color(t["ink"])
    ax.grid(axis="y", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def load():
    by_lot = {}
    summary = {}
    for zone in ZONES:
        name = os.path.join(RESULT_DIR, DATA_FILE + "_" + zone + TAIL)
        by_lot[zone] = pd.read_csv(name + "_by_lot.csv", encoding="utf-8-sig").set_index("LOT_NO")
        summary[zone] = pd.read_csv(name + "_summary.csv", encoding="utf-8-sig").set_index("모델")
    return by_lot, summary


def lot_table(by_lot):
    lots = list(next(iter(by_lot.values())).index)
    rows = []
    for lot in lots:
        row = {"LOT": str(lot)[-3:]}
        for col, short, _ in MODELS:
            vals = []
            for zone in ZONES:
                v = by_lot[zone].loc[lot, col]
                if not pd.isna(v):
                    vals.append(v)
            row[short] = float(np.mean(vals)) if vals else np.nan
        row["정답 1"] = int(sum(by_lot[zone].loc[lot, "LABEL 1"] for zone in ZONES))
        rows.append(row)
    return pd.DataFrame(rows)


def chart_lot_f1(table, theme):
    t = theme_colors(theme)
    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=150)
    fig.patch.set_facecolor(t["bg"])
    style(ax, t)
    x = np.arange(len(table))
    width = 0.26
    for i, (col, short, color) in enumerate(MODELS):
        vals = table[short].values
        bars = ax.bar(x + (i - 1) * width, np.nan_to_num(vals), width, label=short, color=model_color(color, theme), alpha=0.9)
        mean = np.nanmean(vals)
        ax.axhline(mean, color=model_color(color, theme), linewidth=1, linestyle="--", alpha=0.6)
        ax.text(len(table) - 0.45, 0.93 - i * 0.06, "%s 평균의 평균 %.3f" % (short, mean), color=model_color(color, theme), fontsize=10, ha="right", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["LOT %s\n정답 %d분" % (r["LOT"], r["정답 1"]) for _, r in table.iterrows()], fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1 (정답 1이 있는 구역의 평균)")
    ax.set_title("시험 LOT별 F1 — v7 정답, v6 최종 입력, 시간 순서대로 10번 시험", fontsize=14, loc="left", pad=14, color=t["ink"])
    leg = ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=10)
    for txt in leg.get_texts():
        txt.set_color(t["ink"])
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "lot_f1-%s.png" % theme), facecolor=t["bg"])
    plt.close(fig)


def chart_heatmap(by_lot, theme):
    t = theme_colors(theme)
    lots = list(next(iter(by_lot.values())).index)
    mat = np.full((len(ZONES), len(lots)), np.nan)
    pos = np.zeros((len(ZONES), len(lots)), dtype=int)
    for i, zone in enumerate(ZONES):
        for j, lot in enumerate(lots):
            mat[i, j] = by_lot[zone].loc[lot, "RandomForest"]
            pos[i, j] = int(by_lot[zone].loc[lot, "LABEL 1"])
    fig, ax = plt.subplots(figsize=(12, 5.6), dpi=150)
    fig.patch.set_facecolor(t["bg"])
    ax.set_facecolor(t["bg"])
    cmap = plt.get_cmap("YlGn" if theme == "light" else "summer")
    masked = np.ma.masked_invalid(mat)
    im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(len(ZONES)):
        for j in range(len(lots)):
            if np.isnan(mat[i, j]):
                ax.text(j, i, "정답 없음", ha="center", va="center", fontsize=8, color=t["sub"])
            else:
                dark_cell = mat[i, j] < 0.5 if theme == "dark" else mat[i, j] > 0.6
                ax.text(j, i, "%.2f\n(%d분)" % (mat[i, j], pos[i, j]), ha="center", va="center", fontsize=8.5,
                        color=("#e9f2e8" if dark_cell else "#15201a"))
    ax.set_xticks(range(len(lots)))
    ax.set_xticklabels(["LOT %s" % str(l)[-3:] for l in lots], fontsize=10, color=t["sub"])
    ax.set_yticks(range(len(ZONES)))
    ax.set_yticklabels(ZONES, fontsize=11, color=t["sub"])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("구역 × 시험 LOT RandomForest F1 (괄호는 그 LOT, 구역의 정답 1 분 수) — v7", fontsize=14, loc="left", pad=14, color=t["ink"])
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cbar.ax.tick_params(colors=t["sub"], labelsize=9)
    cbar.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "heatmap-%s.png" % theme), facecolor=t["bg"])
    plt.close(fig)


def chart_zone_f1(summary, theme):
    t = theme_colors(theme)
    fig, ax = plt.subplots(figsize=(12, 4.8), dpi=150)
    fig.patch.set_facecolor(t["bg"])
    style(ax, t)
    x = np.arange(len(ZONES))
    width = 0.26
    for i, (col, short, color) in enumerate(MODELS):
        vals = [summary[z].loc[col, "F1"] for z in ZONES]
        ax.bar(x + (i - 1) * width, vals, width, label=short, color=model_color(color, theme), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(["%s\n정답 %d분" % (z, int(summary[z].loc["RandomForest", "LABEL 1"])) for z in ZONES], fontsize=10)
    ax.set_ylim(0, 1)
    ax.axhline(0.6, color=t["sub"], linewidth=1, linestyle=":")
    ax.text(len(ZONES) - 0.5, 0.615, "0.6", color=t["sub"], fontsize=9, ha="right")
    ax.set_ylabel("F1 (시험 10 LOT 합산)")
    ax.set_title("구역별 F1 — 팀 판단이 있는 Z4만 0.6에 닿고, 정답 1이 몇 분뿐인 구역은 어느 모델도 점수가 없음", fontsize=14, loc="left", pad=14, color=t["ink"])
    leg = ax.legend(frameon=False, loc="upper right", ncol=3, fontsize=10)
    for txt in leg.get_texts():
        txt.set_color(t["ink"])
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "zone_f1-%s.png" % theme), facecolor=t["bg"])
    plt.close(fig)


if __name__ == "__main__":
    by_lot, summary = load()
    table = lot_table(by_lot)
    print(table.round(3).to_string(index=False))
    for theme in ["dark", "light"]:
        chart_lot_f1(table, theme)
        chart_heatmap(by_lot, theme)
        chart_zone_f1(summary, theme)
    print("charts written")
