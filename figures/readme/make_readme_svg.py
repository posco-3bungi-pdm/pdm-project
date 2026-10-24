"""README용 애니메이션 SVG 만들기 (다크, 라이트 두 벌)

실행 (저장소 루트에서):
    python figures/readme/make_readme_svg.py

- 외부 도구 없이 문자열로 SVG를 씀. 애니메이션은 SVG 표준(SMIL)이라 GitHub README에서 그대로 움직임
- 만드는 파일: hero, flow, walkforward, labels, domain (각각 -dark.svg, -light.svg)
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"

THEMES = {
    "dark": {"bg": "#0b0f0c", "panel": "#131b15", "ink": "#e9f2e8", "sub": "#9fb39d", "accent": "#a8ff3e",
             "warm": "#ffb347", "hot": "#ff5a5f", "cool": "#5ec8ff", "grid": "#22312a", "muted": "#3b4b3f", "line": "#34463a"},
    "light": {"bg": "#ffffff", "panel": "#f3f7f2", "ink": "#15201a", "sub": "#5a6b5c", "accent": "#3f8f1a",
              "warm": "#e07b00", "hot": "#d8323a", "cool": "#1f7fb8", "grid": "#e1e8df", "muted": "#cbd5c9", "line": "#c3cfc1"},
}

ZONES = [("CLN", "세정", "cool"), ("Z1", "건조", "warm"), ("Z2", "예열", "warm"), ("Z3", "가열", "hot"), ("Z4", "가열", "hot"),
         ("Z5", "균열", "hot"), ("Z6", "균열", "hot"), ("Z7", "과시효", "warm"), ("Z8", "과시효", "warm"), ("Z9", "서냉", "warm"),
         ("OUT", "냉각", "cool")]

LOTS = [("001", "SGCC", "1/2"), ("024", "SPFH590", "3/7"), ("037", "SPCE", "4/13"), ("038", "SPCEN", "4/16"),
        ("044", "SPHC", "5/3"), ("058", "DP590", "6/9"), ("061", "SPHC", "6/15"), ("069", "SPHC", "7/7"),
        ("091", "SPHC", "9/8"), ("108", "SPFH590", "10/18"), ("114", "SPCEN", "11/4"), ("117", "SPCD", "11/13"),
        ("121", "SPCE", "11/24"), ("133", "SPCE", "12/28")]


def head(width, height, t):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">\n'
            '<rect width="%d" height="%d" rx="18" fill="%s"/>\n' % (width, height, width, height, FONT, width, height, t["bg"]))


def text(x, y, s, size, fill, weight="normal", anchor="start", extra=""):
    return '<text x="%s" y="%s" font-size="%s" fill="%s" font-weight="%s" text-anchor="%s" %s>%s</text>\n' % (
        x, y, size, fill, weight, anchor, extra, s)


def write(name, theme, body):
    path = os.path.join(HERE, "%s-%s.svg" % (name, theme))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", os.path.relpath(path))


# 1. 머리 배너: 연속 소둔로 11구역이 차례로 켜지고 강판이 지나감
def hero(theme):
    t = THEMES[theme]
    W, H = 1200, 380
    s = head(W, H, t)
    s += ('<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="%s" stop-opacity="0"/>'
          '<stop offset="1" stop-color="%s" stop-opacity="0.18"/></linearGradient></defs>\n' % (t["accent"], t["accent"]))
    s += '<rect width="%d" height="%d" rx="18" fill="url(#g)"/>\n' % (W, H)
    s += text(56, 86, "CAL01 Predictive Maintenance", 20, t["sub"], extra='letter-spacing="2"')
    s += text(56, 140, "연속 소둔로의 흐름을 보고,", 40, t["ink"], "bold")
    s += text(56, 190, "같은 구간을 팀이 함께 판단합니다", 40, t["accent"], "bold")
    s += text(56, 232, "3σ 통계 후보 → 팀 판단 → 규칙으로 정답을 다듬고, 시간 순서를 지켜 모델을 시험합니다", 17, t["sub"])

    chips = [("14 LOT · 345,390 원기록 · 21 센서", t["cool"]),
             ("팀 판단 33건 · 전 구역 검토 81건 · 규칙 2개", t["warm"]),
             ("Z4 F1 0.60 (Z-score) · 0.59 (RandomForest)", t["accent"])]
    x = 56
    for label, col in chips:
        w = 12 + len(label) * 9.2
        s += '<rect x="%d" y="262" width="%d" height="34" rx="17" fill="%s" fill-opacity="0.12" stroke="%s" stroke-opacity="0.6"/>\n' % (
            x, w, col, col)
        s += text(x + w / 2, 285, label, 14, t["ink"], anchor="middle")
        x += w + 12

    bx, by, bw, bh, gap = 56, 318, 92, 34, 6
    for i, (zone, name, kind) in enumerate(ZONES):
        x0 = bx + i * (bw + gap)
        col = t[kind]
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" fill-opacity="0.18" stroke="%s" stroke-opacity="0.5">' % (
            x0, by, bw, bh, col, col)
        s += '<animate attributeName="fill-opacity" values="0.18;0.9;0.18" keyTimes="0;0.5;1" dur="6s" begin="%.2fs" repeatCount="indefinite"/></rect>\n' % (
            i * 0.45)
        s += text(x0 + bw / 2, by + 22, zone, 14, t["ink"], "bold", "middle")
    y_line = by + bh / 2
    x_end = bx + 11 * (bw + gap) + 20
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" stroke-dasharray="6 6"/>\n' % (
        bx - 30, y_line, x_end, y_line, t["line"])
    s += '<circle r="6" fill="%s"><animateMotion dur="6s" repeatCount="indefinite" path="M %d %d L %d %d"/></circle>\n' % (
        t["accent"], bx - 30, y_line, x_end, y_line)
    s += "</svg>\n"
    write("hero", theme, s)


# 2. 시스템 구성: 분석 저장소 → 검토 사이트 → 관제 (점선이 흐름)
def flow(theme):
    t = THEMES[theme]
    W, H = 1200, 316
    s = head(W, H, t)
    cards = [("pdm-project", "분석 저장소", ["06 ~ 13 정답 만들기 (v1 → v7)", "03 모델 비교 (Dummy, Z-score, IF, RF)", "05 관제용 모델 저장 (registry)"], t["accent"]),
             ("cal01-review", "공동 검토 사이트", ["3σ 후보와 모델 후보를 그래프로 봄", "팀이 1, 0, 보류를 남김 (T, S, M)", "검토 표 CSV로 내보냄"], t["warm"]),
             ("cal01-monitor", "소둔로 관제", ["3D 소둔로와 채널 위치", "Z-score 경보와 현장 요청", "구역별 모델을 레지스트리에서 읽음"], t["cool"])]
    cw, ch = 340, 190
    xs = [50, 430, 810]
    for (title, sub, lines, col), x in zip(cards, xs):
        s += '<rect x="%d" y="60" width="%d" height="%d" rx="16" fill="%s" stroke="%s" stroke-opacity="0.7"/>\n' % (x, cw, ch, t["panel"], col)
        s += '<rect x="%d" y="60" width="6" height="%d" rx="3" fill="%s"/>\n' % (x, ch, col)
        s += text(x + 24, 96, title, 22, t["ink"], "bold")
        s += text(x + 24, 120, sub, 14, col)
        for i, line in enumerate(lines):
            s += text(x + 24, 156 + i * 26, "• " + line, 14, t["sub"])
    for x in [390, 770]:
        s += ('<line x1="%d" y1="155" x2="%d" y2="155" stroke="%s" stroke-width="3" stroke-dasharray="8 8">'
              '<animate attributeName="stroke-dashoffset" from="32" to="0" dur="1.2s" repeatCount="indefinite"/></line>\n' % (x, x + 40, t["sub"]))
        s += '<polygon points="%d,148 %d,155 %d,162" fill="%s"/>\n' % (x + 34, x + 44, x + 34, t["sub"])
    s += ('<path d="M 600 250 C 600 276, 220 276, 220 252" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="6 6">'
          '<animate attributeName="stroke-dashoffset" from="24" to="0" dur="1.2s" repeatCount="indefinite"/></path>\n' % t["warm"])
    s += text(410, 300, "팀 판단이 검토 표로 돌아와 다음 정답(v6, v7)이 됨", 13, t["warm"], anchor="middle")
    s += text(W / 2, 36, "세 저장소가 한 흐름으로 이어집니다", 16, t["sub"], anchor="middle")
    s += "</svg>\n"
    write("flow", theme, s)


# 3. 시계열 걷기: 앞 4개 LOT 학습, 다음 LOT 시험을 10번
def walkforward(theme):
    t = THEMES[theme]
    W, H = 1200, 330
    s = head(W, H, t)
    s += text(W / 2, 40, "시간 순서를 지키는 시험: 앞 LOT으로 배우고, 바로 다음 LOT 하나를 맞힙니다 (10번 반복)", 17, t["ink"], "bold", "middle")
    bw, gap, bx, by, bh = 72, 8, 50, 96, 86
    steps = 10
    dur = 20.0
    key_times = ";".join("%.3f" % (k / steps) for k in range(steps + 1))
    for i, (lot, grade, date) in enumerate(LOTS):
        x0 = bx + i * (bw + gap)
        fills = []
        for k in range(steps):
            test_i = 4 + k
            if i < test_i:
                fills.append(t["accent"])
            elif i == test_i:
                fills.append(t["hot"])
            else:
                fills.append(t["muted"])
        fills.append(fills[-1])
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="2">' % (
            x0, by, bw, bh, fills[0], fills[0])
        s += '<animate attributeName="fill" values="%s" keyTimes="%s" calcMode="discrete" dur="%ss" repeatCount="indefinite"/>' % (
            ";".join(fills), key_times, dur)
        s += '<animate attributeName="stroke" values="%s" keyTimes="%s" calcMode="discrete" dur="%ss" repeatCount="indefinite"/></rect>\n' % (
            ";".join(fills), key_times, dur)
        s += text(x0 + bw / 2, by + 34, lot, 18, t["ink"], "bold", "middle")
        s += text(x0 + bw / 2, by + 56, grade, 11, t["sub"], anchor="middle")
        s += text(x0 + bw / 2, by + 74, date, 11, t["sub"], anchor="middle")
    for k in range(steps):
        lot = LOTS[4 + k][0]
        vis = ["0"] * (steps + 1)
        vis[k] = "1"
        s += '<text x="%d" y="226" font-size="16" fill="%s" text-anchor="middle" opacity="0">시험 %d / 10 : 앞의 %d개 LOT으로 배우고 LOT %s를 맞힘' % (
            W / 2, t["ink"], k + 1, 4 + k, lot)
        s += '<animate attributeName="opacity" values="%s" keyTimes="%s" calcMode="discrete" dur="%ss" repeatCount="indefinite"/></text>\n' % (
            ";".join(vis), key_times, dur)
    lx = 50
    for label, col in [("학습에 씀", t["accent"]), ("지금 시험하는 LOT", t["hot"]), ("아직 안 본 미래", t["muted"])]:
        s += '<rect x="%d" y="256" width="16" height="16" rx="4" fill="%s" fill-opacity="0.6"/>\n' % (lx, col)
        s += text(lx + 24, 269, label, 13, t["sub"])
        lx += 24 + len(label) * 13 + 30
    s += text(W - 50, 269, "10번의 시험 결과를 모두 합쳐 F1을 냅니다 · 첫 4개 LOT은 학습에만 씀 · random_state = 42", 13, t["sub"], anchor="end")
    s += text(W - 50, 300, "LOT 번호가 곧 시간 순서 (2024-01 → 2024-12). 미래 값은 입력에도, 통계에도 쓰지 않음", 12, t["sub"], anchor="end")
    s += "</svg>\n"
    write("walkforward", theme, s)


# 4. 정답 v1 → v7: 한 LOT의 60분을 예로, 버전마다 1이 어떻게 바뀌나
def labels(theme):
    t = THEMES[theme]
    W, H = 1200, 420
    s = head(W, H, t)
    s += text(W / 2, 40, "정답(라벨)은 일곱 번 다듬었습니다 — 60분짜리 예시 구간에서 1(빨강)이 줄어드는 모습", 17, t["ink"], "bold", "middle")
    base = list("0000SS0000S00000SSSS0000S0000000SS000S0000000SSS00000S000000")
    rows = [("v1", "LOT 전체 3σ를 넘으면 1 (통계 후보)"),
            ("v2 · v3", "공통 움직임은 팀이 해제 → 0 (C, E, J 검토 282건)"),
            ("v4 · v5", "1초 기록을 1분으로 묶음 (단위만 바뀜)"),
            ("v6", "팀 판단 T 29건 (1은 14건) + 전 구역 검토 S 80건"),
            ("v7", "모델 후보 M 60건 판단 + 규칙 2개: 출력만 넘은 분, 0.5℃ 미만 튐은 0")]

    def pattern(version):
        p = list(base)
        if version >= 1:
            for i in [16, 17, 18, 19, 32, 33]:
                p[i] = "C"
        if version >= 3:
            for i in [45, 46, 47]:
                p[i] = "T"
            p[10] = "X"
        if version >= 4:
            for i in [4, 5, 24, 37]:
                p[i] = "O"
        return p

    colors = {"0": t["muted"], "S": t["hot"], "C": t["sub"], "T": t["accent"], "X": t["sub"], "O": t["cool"]}
    opac = {"0": 0.25, "S": 0.9, "C": 0.35, "T": 1.0, "X": 0.35, "O": 0.35}
    cell, cgap, x0 = 11, 3, 170
    for r, (ver, desc) in enumerate(rows):
        y = 78 + r * 58
        begin = r * 1.6
        s += '<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.9;1" dur="10s" begin="%.1fs" repeatCount="indefinite"/>\n' % begin
        s += text(x0 - 16, y + 12, ver, 15, t["ink"], "bold", "end")
        p = pattern(r)
        for i, st in enumerate(p):
            s += '<rect x="%d" y="%d" width="%d" height="16" rx="3" fill="%s" fill-opacity="%s"/>\n' % (
                x0 + i * (cell + cgap), y, cell, colors[st], opac[st])
        ones = sum(1 for v in p if v in "ST")
        s += text(x0 + 60 * (cell + cgap) + 16, y + 12, "1 = %d분" % ones, 13, t["ink"], "bold")
        s += text(x0 + 60 * (cell + cgap) + 90, y + 12, desc, 13, t["sub"])
        s += "</g>\n"
    lx = 170
    for label, st in [("통계 후보 1", "S"), ("공통 움직임으로 해제 0", "C"), ("팀 판단 1", "T"), ("팀 판단 0 · 모델 후보 0", "X"), ("출력만 넘어 규칙으로 0", "O")]:
        s += '<rect x="%d" y="372" width="14" height="14" rx="3" fill="%s" fill-opacity="%s"/>\n' % (lx, colors[st], max(opac[st], 0.5))
        s += text(lx + 20, 384, label, 12, t["sub"])
        lx += 20 + len(label) * 12 + 26
    s += text(W - 40, 408, "예시 패턴입니다. 실제 분 수는 README 결과 표를 보세요", 11, t["sub"], anchor="end")
    s += "</svg>\n"
    write("labels", theme, s)


# 5. 도메인 연결: CP 이상 뒤에 따라온 정비
def domain(theme):
    t = THEMES[theme]
    W, H = 1200, 300
    s = head(W, H, t)
    s += text(W / 2, 40, "CP(가스 분위기) 센서가 혼자 튄 LOT 뒤에는 정비가 따라왔습니다 (2024년)", 17, t["ink"], "bold", "middle")

    def xpos(month, day):
        doy = sum([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:month - 1]) + day
        return 80 + (doy / 366.0) * 1040

    y = 150
    s += '<line x1="80" y1="%d" x2="1120" y2="%d" stroke="%s" stroke-width="2"/>\n' % (y, y, t["line"])
    for m in range(1, 13):
        x = xpos(m, 1)
        s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>\n' % (x, y - 6, x, y + 6, t["line"])
        s += text(x + 3, y + 24, "%d월" % m, 11, t["sub"])
    lot_days = [(1, 2), (3, 7), (4, 13), (4, 16), (5, 3), (6, 9), (6, 15), (7, 7), (9, 8), (10, 18), (11, 4), (11, 13), (11, 24), (12, 28)]
    for (m, d), (lot, _, _) in zip(lot_days, LOTS):
        x = xpos(m, d)
        s += '<circle cx="%d" cy="%d" r="4" fill="%s"/>\n' % (x, y, t["sub"])
    events = [((4, 14), "037 CP 튐 (T09)", "6시간 뒤 상태 점검", 1),
              ((6, 9), "058 CP 하강 (T12)", "22시간 뒤 O링·오일씰 교체", 2),
              ((7, 8), "069 CP 급등 (T01)", "2시간 뒤 전기 BM, O링 교체 · 16일 뒤 가스 분석계 셀 교체", 1),
              ((9, 9), "091 CP 튐 (T32)", "2.5일 뒤 전기 BM 절연 저하", 2)]
    for (m, d), title, after, lane in events:
        x = xpos(m, d)
        s += ('<circle cx="%d" cy="%d" r="9" fill="%s" fill-opacity="0.25" stroke="%s" stroke-width="2">'
              '<animate attributeName="r" values="9;15;9" dur="2.4s" repeatCount="indefinite"/>'
              '<animate attributeName="fill-opacity" values="0.25;0.05;0.25" dur="2.4s" repeatCount="indefinite"/></circle>\n' % (x, y, t["hot"], t["hot"]))
        ty = 92 if lane == 1 else 215
        s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-dasharray="3 3"/>\n' % (x, y, x, ty + (8 if lane == 1 else -22), t["hot"])
        s += text(x, ty, title, 13, t["ink"], "bold", "middle")
        s += text(x, ty + 18, "→ " + after, 12, t["warm"], anchor="middle")
    s += text(W / 2, 282, "CP 이상 뒤에 부품을 간 두 번 모두 O링(밀봉)이 들어 있고, 069는 CP를 재는 가스 분석계 셀까지 이어집니다 · 함께 나타났다는 뜻이지 원인 증명은 아닙니다", 12, t["sub"], anchor="middle")
    s += "</svg>\n"
    write("domain", theme, s)


if __name__ == "__main__":
    for theme in THEMES:
        hero(theme)
        flow(theme)
        walkforward(theme)
        labels(theme)
        domain(theme)
