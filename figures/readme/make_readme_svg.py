"""README용 애니메이션 SVG 만들기 (다크, 라이트 두 벌)

실행 (저장소 루트에서):
    python figures/readme/make_readme_svg.py

- 외부 도구 없이 문자열로 SVG를 씀. 애니메이션은 SVG 표준(SMIL)이라 GitHub README에서 그대로 움직임
- 양각(올라온 판), 음각(파인 홈), 겹친 도형으로 입체감을 냄. 필터는 SVG 표준(feDropShadow, feGaussianBlur, feTurbulence)만 씀
- 만드는 파일: flow, labels, domain (각각 -dark.svg, -light.svg). hero, walkforward는 make_readme_motion.py가 만듦
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"

THEMES = {
    "dark": {"bg": "#0d110e", "bg2": "#161d17", "plate": "#1a231c", "plate2": "#212c23", "deep": "#080b09",
             "ink": "#eef4ec", "sub": "#9fb39d", "accent": "#a8ff3e", "warm": "#ffb347", "hot": "#ff5a5f", "cool": "#5ec8ff",
             "hi": "#ffffff", "lo": "#000000", "hi_a": "0.10", "lo_a": "0.55", "shadow_a": "0.45", "grain_a": "0.05"},
    "light": {"bg": "#eef1ea", "bg2": "#e4e9df", "plate": "#f7f9f4", "plate2": "#eef2ea", "deep": "#d9dfd4",
              "ink": "#17221b", "sub": "#5b6b5d", "accent": "#3f8f1a", "warm": "#d9741a", "hot": "#d8323a", "cool": "#1f7fb8",
              "hi": "#ffffff", "lo": "#1a2a1e", "hi_a": "0.9", "lo_a": "0.18", "shadow_a": "0.18", "grain_a": "0.06"},
}

ZONES = [("CLN", "cool"), ("Z1", "warm"), ("Z2", "warm"), ("Z3", "hot"), ("Z4", "hot"), ("Z5", "hot"), ("Z6", "hot"),
         ("Z7", "warm"), ("Z8", "warm"), ("Z9", "warm"), ("OUT", "cool")]

LOTS = [("001", "SGCC", "1/2"), ("024", "SPFH590", "3/7"), ("037", "SPCE", "4/13"), ("038", "SPCEN", "4/16"),
        ("044", "SPHC", "5/3"), ("058", "DP590", "6/9"), ("061", "SPHC", "6/15"), ("069", "SPHC", "7/7"),
        ("091", "SPHC", "9/8"), ("108", "SPFH590", "10/18"), ("114", "SPCEN", "11/4"), ("117", "SPCD", "11/13"),
        ("121", "SPCE", "11/24"), ("133", "SPCE", "12/28")]


# ---------------------------------------------------------------- 공통 부품
def defs(t):
    return (
        '<defs>\n'
        '<filter id="shadow" x="-10%%" y="-10%%" width="120%%" height="140%%"><feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#000" flood-opacity="%s"/></filter>\n'
        '<filter id="shadow-sm" x="-10%%" y="-10%%" width="120%%" height="140%%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity="%s"/></filter>\n'
        '<filter id="inset" x="-10%%" y="-10%%" width="120%%" height="130%%">'
        '<feOffset dx="0" dy="3"/><feGaussianBlur stdDeviation="3" result="ob"/>'
        '<feComposite operator="out" in="SourceGraphic" in2="ob" result="inv"/>'
        '<feFlood flood-color="#000" flood-opacity="0.55" result="col"/>'
        '<feComposite operator="in" in="col" in2="inv" result="sh"/>'
        '<feComposite operator="over" in="sh" in2="SourceGraphic"/></filter>\n'
        '<filter id="glow" x="-50%%" y="-50%%" width="200%%" height="200%%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>\n'
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.6 0"/></filter>\n'
        '<linearGradient id="plate" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>\n'
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>\n'
        '<radialGradient id="coin" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="%s" stop-opacity="0.9"/><stop offset="0.55" stop-color="%s" stop-opacity="0"/><stop offset="1" stop-color="%s" stop-opacity="0.35"/></radialGradient>\n'
        '</defs>\n' % (t["shadow_a"], t["shadow_a"], t["plate"], t["plate2"], t["bg"], t["bg2"], t["hi"], t["hi"], t["lo"]))


def head(width, height, t):
    s = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">\n'
         % (width, height, width, height, FONT))
    s += defs(t)
    s += '<rect width="%d" height="%d" rx="22" fill="url(#bg)"/>\n' % (width, height)
    s += '<rect width="%d" height="%d" rx="22" filter="url(#grain)" opacity="%s"/>\n' % (width, height, t["grain_a"])
    return s


def text(x, y, s, size, fill, weight="normal", anchor="start", extra=""):
    return '<text x="%s" y="%s" font-size="%s" fill="%s" font-weight="%s" text-anchor="%s" %s>%s</text>\n' % (
        x, y, size, fill, weight, anchor, extra, s)


def emboss_text(t, x, y, s, size, fill, weight="bold", anchor="start"):
    """글자를 양각처럼: 아래 그림자, 위 하이라이트, 본글자 세 겹"""
    out = text(x + 1, y + 2, s, size, t["lo"], weight, anchor, 'opacity="%s"' % t["lo_a"])
    out += text(x - 1, y - 1, s, size, t["hi"], weight, anchor, 'opacity="%s"' % t["hi_a"])
    out += text(x, y, s, size, fill, weight, anchor)
    return out


def raised(t, x, y, w, h, r=16, fill="url(#plate)", back=True, edge=None):
    """올라온 판: 뒤에 어긋난 판 한 겹, 그림자, 윗변 하이라이트, 아랫변 그늘"""
    s = ""
    if back:
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" opacity="0.55"/>\n' % (x + 10, y + 12, w, h, r, t["deep"])
    s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" filter="url(#shadow)"/>\n' % (x, y, w, h, r, fill)
    if edge:
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="none" stroke="%s" stroke-opacity="0.55" stroke-width="1.5"/>\n' % (x, y, w, h, r, edge)
    s += '<path d="M %d %d L %d %d Q %d %d %d %d L %d %d" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (
        x + 1, y + h - r, x + 1, y + r, x + 1, y + 1, x + r, y + 1, x + w - r, y + 1, t["hi"], t["hi_a"])
    s += '<path d="M %d %d L %d %d Q %d %d %d %d L %d %d" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (
        x + r, y + h - 1, x + w - r, y + h - 1, x + w - 1, y + h - 1, x + w - 1, y + h - r, x + w - 1, y + r, t["lo"], t["lo_a"])
    return s


def inset(t, x, y, w, h, r=12, fill=None):
    """파인 홈(음각): 안쪽 그림자 필터, 아랫변 하이라이트"""
    fill = fill or t["deep"]
    s = '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" filter="url(#inset)"/>\n' % (x, y, w, h, r, fill)
    s += '<path d="M %d %d L %d %d" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (x + r, y + h + 1, x + w - r, y + h + 1, t["hi"], t["hi_a"])
    return s


def groove(t, x1, y1, x2, y2, dash=""):
    """새긴 홈 선: 어두운 선 위에 밝은 선 한 겹"""
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    s = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="%s" stroke-width="3"%s/>\n' % (x1, y1, x2, y2, t["lo"], t["lo_a"], d)
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="%s" stroke-width="1.5"%s/>\n' % (x1, y1 + 2, x2, y2 + 2, t["hi"], t["hi_a"], d)
    return s


def coin(t, cx, cy, r, fill, extra=""):
    """볼록한 단추: 색 원 + 하이라이트 원 + 그림자"""
    s = '<circle cx="%d" cy="%d" r="%d" fill="%s" filter="url(#shadow-sm)"%s/>\n' % (cx, cy, r, fill, extra)
    s += '<circle cx="%d" cy="%d" r="%d" fill="url(#coin)"/>\n' % (cx, cy, r)
    return s


def pipe(t, x1, x2, y, col, label="", dur=1.6):
    """연결 관: 파인 홈 속을 빛 덩이가 지나가고 끝에 화살촉. label은 무엇이 흐르는지"""
    s = inset(t, x1, y - 8, x2 - x1 - 10, 16, 8)
    s += '<polygon points="%d,%d %d,%d %d,%d" fill="%s" filter="url(#shadow-sm)"/>\n' % (x2 - 14, y - 11, x2, y, x2 - 14, y + 11, col)
    for begin in [0, dur / 2]:
        s += ('<rect x="%d" y="%d" width="26" height="8" rx="4" fill="%s" filter="url(#glow)" opacity="0">'
              '<animate attributeName="x" from="%d" to="%d" dur="%ss" begin="%ss" repeatCount="indefinite"/>'
              '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.85;1" dur="%ss" begin="%ss" repeatCount="indefinite"/></rect>\n'
              % (x1 + 2, y - 4, col, x1 + 2, x2 - 40, dur, begin, dur, begin))
    if label:
        s += text((x1 + x2) / 2 - 5, y - 16, label, 11, t["sub"], anchor="middle")
    return s


def curve_pipe(t, d, col, label="", lx=0, ly=0, dur=2.4):
    """굽은 관: 홈 선 위로 캡슐이 경로(d)를 따라 감. 화살촉은 호출 쪽에서 붙임"""
    s = '<path d="%s" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="10" stroke-linecap="round"/>\n' % (d, t["lo"], t["lo_a"])
    s += '<path d="%s" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="3" stroke-linecap="round"/>\n' % (d, t["hi"], t["hi_a"])
    s += '<path d="%s" fill="none" stroke="%s" stroke-opacity="0.35" stroke-width="2"/>\n' % (d, col)
    s += ('<rect x="-14" y="-4" width="28" height="8" rx="4" fill="%s" filter="url(#glow)">'
          '<animateMotion dur="%ss" repeatCount="indefinite" rotate="auto" path="%s"/></rect>\n' % (col, dur, d))
    if label:
        s += text(lx, ly, label, 11.5, col, "bold", "middle")
    return s


def up_arrow(t, x, y, col):
    return '<polygon points="%d,%d %d,%d %d,%d" fill="%s" filter="url(#shadow-sm)"/>\n' % (x - 9, y + 10, x + 9, y + 10, x, y - 4, col)


def pill(t, x, y, label, col, size=14):
    w = 26 + len(label) * size * 0.68
    s = raised(t, x, y, w, 36, 18, back=False, edge=col)
    s += coin(t, x + 18, y + 18, 7, col)
    s += text(x + 34, y + 23, label, size, t["ink"])
    return s, w


def layered_decor(t, x, y, r, col):
    """뒤에 겹쳐 둔 원 세 개 (종이를 포갠 느낌)"""
    s = ""
    for i, op in enumerate(["0.05", "0.08", "0.12"]):
        s += '<circle cx="%d" cy="%d" r="%d" fill="%s" opacity="%s"/>\n' % (x - i * 26, y + i * 18, r - i * 28, col, op)
    return s


def write(name, theme, body):
    path = os.path.join(HERE, "%s-%s.svg" % (name, theme))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", os.path.relpath(path))


# ---------------------------------------------------------------- 2. 세 저장소 흐름
def flow(theme):
    t = THEMES[theme]
    W, H = 1200, 404
    s = head(W, H, t)
    s += layered_decor(t, 1120, 40, 150, t["cool"])
    s += emboss_text(t, 56, 48, "세 저장소가 한 흐름으로 이어짐", 20, t["ink"])
    cards = [("pdm-project", "분석 저장소", ["06 ~ 13 정답 만들기 (v1 → v7)", "03 모델 비교 (Dummy, Z-score, IF, RF)", "05 관제용 모델 저장 (registry)"], t["accent"]),
             ("cal01-review", "공동 검토 사이트", ["3σ 후보와 모델 후보를 그래프로 봄", "팀이 1, 0, 보류를 남김 (T, S, M)", "검토 표 CSV로 내보냄"], t["warm"]),
             ("cal01-monitor", "소둔로 관제", ["3D 소둔로와 채널 위치", "Z-score 경보와 현장 요청", "구역별 모델을 레지스트리에서 읽음"], t["cool"])]
    cw, ch, y0 = 320, 196, 78
    xs = [56, 440, 824]
    for (title, sub, lines, col), x in zip(cards, xs):
        s += raised(t, x, y0, cw, ch, 18)
        # 왼쪽 색 기둥 (둥근 막대)
        s += '<rect x="%d" y="%d" width="10" height="%d" rx="5" fill="%s" filter="url(#shadow-sm)"/>\n' % (x + 16, y0 + 18, ch - 36, col)
        s += '<rect x="%d" y="%d" width="3" height="%d" rx="1.5" fill="%s" opacity="0.5"/>\n' % (x + 18, y0 + 22, ch - 44, t["hi"])
        s += emboss_text(t, x + 42, y0 + 46, title, 22, t["ink"])
        s += text(x + 42, y0 + 70, sub, 14, col)
        # 항목은 파인 홈 안에
        s += inset(t, x + 38, y0 + 86, cw - 56, 92, 10)
        for i, line in enumerate(lines):
            s += coin(t, x + 54, y0 + 106 + i * 28, 4, col)
            s += text(x + 66, y0 + 111 + i * 28, line, 13, t["ink"])
    # 관 1: 후보가 검토 사이트로. 관 2: 팀 판단이 관제의 과거 LOT 화면으로
    s += pipe(t, 376, 440, y0 + 100, t["warm"], "후보 (3σ, 모델)")
    s += pipe(t, 760, 824, y0 + 100, t["cool"], "팀 판단")
    # 굽은 관 1: 검토 표가 분석 저장소로 돌아와 다음 정답이 됨
    d1 = "M 600 %d C 600 %d, 216 %d, 216 %d" % (y0 + ch + 2, y0 + ch + 50, y0 + ch + 50, y0 + ch + 4)
    s += curve_pipe(t, d1, t["warm"], "검토 표 → 정답 v6, v7", 408, y0 + ch + 72)
    s += up_arrow(t, 216, y0 + ch - 2, t["warm"])
    # 굽은 관 2: 05 노트북이 저장한 모델이 관제로 (카드 아래로 지나감)
    d2 = "M 300 %d C 300 %d, 984 %d, 984 %d" % (y0 + ch + 2, y0 + ch + 96, y0 + ch + 96, y0 + ch + 4)
    s += curve_pipe(t, d2, t["accent"], "모델 registry (05 노트북)", 642, y0 + ch + 116, dur=3.2)
    s += up_arrow(t, 984, y0 + ch - 2, t["accent"])
    s += "</svg>\n"
    write("flow", theme, s)


# ---------------------------------------------------------------- 4. 정답 v1 → v7
def labels(theme):
    t = THEMES[theme]
    W, H = 1200, 440
    s = head(W, H, t)
    s += layered_decor(t, 1130, 60, 150, t["hot"])
    s += emboss_text(t, 56, 48, "정답(라벨)은 일곱 번 다듬음 — 60분짜리 예시 구간에서 1(빨강)이 줄어드는 모습", 18, t["ink"])
    base = list("0000SS0000S00000SSSS0000S0000000SS000S0000000SSS00000S000000")
    rows = [("v1", "LOT 전체 3σ를 넘으면 1 (통계 후보)"),
            ("v2 · v3", "공통 움직임은 팀이 해제 → 0 (C, E, J, A 216건)"),
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

    colors = {"0": t["plate2"], "S": t["hot"], "C": t["sub"], "T": t["accent"], "X": t["sub"], "O": t["cool"]}
    opac = {"0": 0.6, "S": 0.95, "C": 0.35, "T": 1.0, "X": 0.35, "O": 0.4}
    cell, cgap, x0 = 11, 3, 176
    tray_w = 60 * (cell + cgap) + 20
    s += inset(t, x0 - 10, 70, tray_w, 5 * 58 + 10, 14)
    for r, (ver, desc) in enumerate(rows):
        y = 86 + r * 58
        begin = r * 1.6
        s += '<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.9;1" dur="10s" begin="%.1fs" repeatCount="indefinite"/>\n' % begin
        s += emboss_text(t, x0 - 24, y + 13, ver, 15, t["ink"], anchor="end")
        p = pattern(r)
        for i, st in enumerate(p):
            cx = x0 + i * (cell + cgap)
            s += '<rect x="%d" y="%d" width="%d" height="18" rx="4" fill="%s" fill-opacity="%s" filter="url(#shadow-sm)"/>\n' % (cx, y, cell, colors[st], opac[st])
            s += '<path d="M %d %d L %d %d" stroke="%s" stroke-opacity="%s"/>\n' % (cx + 2, y + 1, cx + cell - 2, y + 1, t["hi"], t["hi_a"])
        ones = sum(1 for v in p if v in "ST")
        s += emboss_text(t, x0 + tray_w + 8, y + 13, "1 = %d분" % ones, 13, t["ink"])
        s += text(x0 + tray_w + 84, y + 13, desc, 13, t["sub"])
        s += "</g>\n"
    lx = 176
    for label, st in [("통계 후보 1", "S"), ("공통 움직임으로 해제 0", "C"), ("팀 판단 1", "T"), ("팀 판단 0 · 모델 후보 0", "X"), ("출력만 넘어 규칙으로 0", "O")]:
        s += coin(t, lx + 7, 392, 7, colors[st])
        s += text(lx + 22, 397, label, 12, t["sub"])
        lx += 22 + len(label) * 12 + 26
    s += text(W - 40, 426, "예시 패턴임. 실제 분 수는 README 결과 표에 있음", 11, t["sub"], anchor="end")
    s += "</svg>\n"
    write("labels", theme, s)


# ---------------------------------------------------------------- 5. 도메인 연결
def domain(theme):
    t = THEMES[theme]
    W, H = 1200, 320
    s = head(W, H, t)
    s += layered_decor(t, 100, 330, 150, t["warm"])
    s += emboss_text(t, 56, 48, "CP(가스 분위기) 센서가 혼자 튄 LOT 뒤에는 정비가 따라옴 (2024년)", 18, t["ink"])

    def xpos(month, day):
        doy = sum([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:month - 1]) + day
        return 80 + (doy / 366.0) * 1040

    y = 170
    s += inset(t, 56, y - 22, 1088, 44, 22)
    s += groove(t, 80, y, 1120, y)
    for m in range(1, 13):
        x = xpos(m, 1)
        s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="0.5"/>\n' % (x, y - 8, x, y + 8, t["sub"])
        s += text(x + 4, y + 38, "%d월" % m, 11, t["sub"])
    lot_days = [(1, 2), (3, 7), (4, 13), (4, 16), (5, 3), (6, 9), (6, 15), (7, 7), (9, 8), (10, 18), (11, 4), (11, 13), (11, 24), (12, 28)]
    for (m, d), (lot, _, _) in zip(lot_days, LOTS):
        s += coin(t, xpos(m, d), y, 5, t["sub"])
    events = [((4, 14), "037 CP 튐 (T09)", "6시간 뒤 상태 점검", 1),
              ((6, 9), "058 CP 하강 (T12)", "22시간 뒤 O링·오일씰 교체", 2),
              ((7, 8), "069 CP 급등 (T01)", "2시간 뒤 전기 BM, O링 교체 · 16일 뒤 가스 분석계 셀 교체", 1),
              ((9, 9), "091 CP 튐 (T32)", "2.5일 뒤 전기 BM 절연 저하", 2)]
    for (m, d), title, after, lane in events:
        x = xpos(m, d)
        s += '<circle cx="%d" cy="%d" r="10" fill="%s" fill-opacity="0.25"><animate attributeName="r" values="10;18;10" dur="2.4s" repeatCount="indefinite"/><animate attributeName="fill-opacity" values="0.25;0;0.25" dur="2.4s" repeatCount="indefinite"/></circle>\n' % (x, y, t["hot"])
        s += coin(t, x, y, 8, t["hot"])
        ty = 96 if lane == 1 else 238
        s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="0.7" stroke-dasharray="3 3"/>\n' % (x, y + (-12 if lane == 1 else 12), x, ty + (14 if lane == 1 else -28), t["hot"])
        tw = 14 + max(len(title), len(after) + 2) * 7.4
        s += raised(t, x - tw / 2, ty - 24, tw, 46, 10, back=False, edge=t["hot"])
        s += emboss_text(t, x, ty - 6, title, 13, t["ink"], anchor="middle")
        s += text(x, ty + 12, "→ " + after, 11.5, t["warm"], anchor="middle")
    s += text(W / 2, 304, "CP 이상 뒤에 부품을 간 두 번 모두 O링(밀봉)이 들어 있고, 069는 CP를 재는 가스 분석계 셀까지 이어짐 · 함께 나타났다는 뜻이지 원인 증명은 아님", 12, t["sub"], anchor="middle")
    s += "</svg>\n"
    write("domain", theme, s)


if __name__ == "__main__":
    for theme in THEMES:
        flow(theme)
        labels(theme)
        domain(theme)
