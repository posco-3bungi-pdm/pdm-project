"""README용 실제 데이터 그림: LOT 069 CP-Z4 1분 기록이 왼쪽부터 그려지고 T01 구간이 켜짐 (다크, 라이트)

실행 (저장소 루트에서, data/processed/cal01_base_v7.csv가 있어야 함. 다른 자리에 있으면 경로를 인자로 줌):
    python figures/readme/make_readme_data_svg.py [cal01_base_v7.csv 경로]

- 값은 CSV 그대로 (교육용 재현 데이터). 선 그리기는 SVG stroke-dashoffset 애니메이션
- 스타일 부품은 make_readme_svg.py의 것을 그대로 씀
"""

import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_readme_svg import THEMES, coin, emboss_text, head, inset, text, write  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
BASE_CSV = os.path.join(ROOT, "data", "processed", "cal01_base_v7.csv")
LOT = 240069
SENSOR = "CP-Z4"
SPANS = [("2024-07-08 02:28", "2024-07-08 02:42", "T01 CP 급등 14분 → 2시간 뒤 전기 BM")]


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else BASE_CSV
    df = pd.read_csv(csv_path, parse_dates=["MEAS_DT"], encoding="utf-8-sig")
    d = df[(df["LOT_NO"] == LOT) & (df["EXCLUDED"] == False)].sort_values("MEAS_DT").reset_index(drop=True)
    values = d[SENSOR].tolist()
    times = d["MEAS_DT"]
    n = len(values)

    W, H = 1200, 340
    x0, x1, y0, y1 = 96, 1140, 86, 258
    lo, hi = 0.42, 0.90  # T01 급등(최대 0.88)이 잘리지 않게

    def xpos(i):
        return x0 + (i / (n - 1)) * (x1 - x0)

    def ypos(v):
        v = min(max(v, lo), hi)
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    points = [(xpos(i), ypos(v)) for i, v in enumerate(values)]
    path = "M " + " L ".join("%.1f %.1f" % pt for pt in points)
    # 선 길이를 실제로 재서 dasharray로 씀 (짧으면 선이 끝까지 안 그려짐)
    length = 0.0
    for (ax, ay), (bx, by) in zip(points[:-1], points[1:]):
        length += math.hypot(bx - ax, by - ay)
    dash = int(length * 1.02) + 10

    def index_at(stamp):
        return int((times >= pd.Timestamp(stamp)).idxmax())

    for theme, t in THEMES.items():
        s = head(W, H, t)
        s += emboss_text(t, 56, 44, "LOT 069 (SPHC, 7/7 16:57 ~ 7/8 06:29) CP-Z4 1분 기록 %d분 — 팀이 1로 확정한 T01이 켜짐" % n, 17, t["ink"])
        # 그래프는 파인 홈 안에
        s += inset(t, x0 - 40, y0 - 22, x1 - x0 + 56, y1 - y0 + 44, 14)
        for g in [0.45, 0.55, 0.65, 0.75, 0.85]:
            gy = ypos(g)
            s += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-opacity="0.35" stroke-width="1"/>\n' % (x0, gy, x1, gy, t["sub"])
            s += text(x0 - 10, gy + 4, "%.2f" % g, 11, t["sub"], anchor="end")
        for a, b, label in SPANS:
            xa, xb = xpos(index_at(a)), xpos(index_at(b))
            s += ('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s" fill-opacity="0">'
                  '<animate attributeName="fill-opacity" values="0;0;0.28;0.28" keyTimes="0;0.78;0.82;1" dur="9s" repeatCount="indefinite"/></rect>\n'
                  % (xa - 2, y0 - 12, max(xb - xa, 8) + 4, y1 - y0 + 24, t["hot"]))
            # 구간이 오른쪽 끝에 가까우면 글자를 왼쪽에 둠 (잘리지 않게)
            if xa > W * 0.6:
                label_svg = coin(t, xb + 14, y0 - 30, 6, t["hot"]) + text(xa - 8, y0 - 26, label, 12.5, t["hot"], "bold", anchor="end")
            else:
                label_svg = coin(t, xa - 14, y0 - 30, 6, t["hot"]) + text(xa - 2, y0 - 26, label, 12.5, t["hot"], "bold")
            s += ('<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.8;0.84;1" dur="9s" repeatCount="indefinite"/>'
                  + label_svg + "</g>\n")
        s += ('<path d="%s" fill="none" stroke="%s" stroke-width="1.7" stroke-linejoin="round" stroke-dasharray="%d" stroke-dashoffset="%d">'
              '<animate attributeName="stroke-dashoffset" values="%d;0;0" keyTimes="0;0.8;1" dur="9s" repeatCount="indefinite"/></path>\n'
              % (path, t["cool"], dash, dash, dash))
        s += text(56, H - 44, "가로: 7/7 17시 → 7/8 06시 1분 평균 (정지·승온 구간은 뺀 813분) · 세로: CP-Z4 · 19시 무렵 작은 튐 6곳은 T02 ~ T07 (정수진 추천, 팀 미확정)", 12, t["sub"])
        s += text(56, H - 24, "2시간 뒤 전기 BM 절연 저하와 O링 교체, 16일 뒤 가스 분석계 셀 교체가 이어짐", 12, t["sub"])
        s += text(W - 56, H - 24, "값은 CSV 그대로 (교육용 재현 데이터)", 11, t["accent"], anchor="end")
        s += "</svg>\n"
        write("lot069-cp", theme, s)


if __name__ == "__main__":
    main()
