# README의 움직이는 그림 3개를 만듦
# - svg     : 시간 순서를 지키는 시험 (코일 14개, SMIL 모핑) → walkforward-light.svg, walkforward-dark.svg
# - hero    : 관제 시뮬레이션 3D 소둔로 녹화 위에 문구와 공정선을 얹은 히어로 → hero.webp
# - monitor : 관제 화면 녹화 16초 → monitor.webp
# 실행 (저장소 루트): uv run --with imageio-ffmpeg --with pillow python figures/readme/make_readme_motion.py svg|hero|monitor
# hero, monitor는 팀 공유 폴더의 녹화(저장소 밖)와 Microsoft Edge가 있어야 함. 녹화 경로는 환경변수 CAL01_SCENE_MP4로 바꿀 수 있음
import glob
import math
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCENE_MP4 = os.environ.get("CAL01_SCENE_MP4", os.path.join(os.path.dirname(ROOT), "영상소스", "장면영상_v2_20261024", "소프트웨어_녹화",
                                                           "09_정렬_홀로그램_부품확인_점선강조.mp4"))
EDGE = os.environ.get("EDGE_EXE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
WORK = os.path.join(tempfile.gettempdir(), "cal01_readme_motion")
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif"


# ---------------------------------------------------------------- 1. 시간 순서를 지키는 시험 (SVG)
LOTS = [("001", "1/2"), ("024", "3/7"), ("037", "4/13"), ("038", "4/16"), ("044", "5/3"), ("058", "6/9"), ("061", "6/15"),
        ("069", "7/7"), ("091", "9/8"), ("108", "10/18"), ("114", "11/4"), ("117", "11/13"), ("121", "11/24"), ("133", "12/28")]
TRAIN_ONLY = 4                    # 처음 4개 LOT은 학습에만 씀
STEPS = len(LOTS) - TRAIN_ONLY    # 시험 10번
STEP_SEC = 2.6                    # 시험 한 번에 걸리는 시간
MOVE_SEC = 0.75                   # 상태가 바뀌는 시간
TOTAL = STEPS * STEP_SEC
SVG_W, SVG_H = 1200, 360
R = 24                            # 코일 세로 반지름
FX = 15                           # 코일 앞면 타원의 가로 반지름
BODY = 26                         # 코일 폭
PITCH = 80
X0 = 80
CY = 170
SPLINE = "0.5 0 0.2 1"

SVG_THEMES = {
    "light": dict(card="#f6f8fa", stroke="#d0d7de", ink="#1f2328", sub="#59636e", faint="#6e7781",
                  steel_hi="#e3e8ee", steel_lo="#a4aebb", ring="#7d8795", hole="#eef1f5", edge="#8a94a3",
                  green_hi="#7ad28f", green_lo="#2f9e4f", green="#2da44e", red_hi="#ff9a8f", red_lo="#d23c32", red="#d1242f",
                  shine="#ffffff", shine_a="0.75", shadow_a="0.16"),
    "dark": dict(card="#0d1117", stroke="#30363d", ink="#e6edf3", sub="#9aa7b4", faint="#8b949e",
                 steel_hi="#7b8794", steel_lo="#3a424d", ring="#232a33", hole="#090c10", edge="#59636f",
                 green_hi="#56d364", green_lo="#1f7a36", green="#3fb950", red_hi="#ff8b80", red_lo="#b62324", red="#f85149",
                 shine="#ffffff", shine_a="0.28", shadow_a="0.45"),
}


def test_index(k):
    return TRAIN_ONLY + k


def key_times():
    """맨 앞 구간이 '시험 10 → 시험 1'로 돌아오는 변화라 반복할 때 끊기지 않음"""
    kt = [0.0]
    sp = []
    for k in range(STEPS):
        kt.append((k * STEP_SEC + MOVE_SEC) / TOTAL)
        sp.append(SPLINE)
        kt.append((k + 1) * STEP_SEC / TOTAL)
        sp.append("0 0 1 1")
    return kt, sp


KT, SP = key_times()


def animate(attr, f, tag="animate", extra=""):
    values = [f(STEPS - 1)]
    for k in range(STEPS):
        values.append(f(k))
        values.append(f(k))
    return '<%s attributeName="%s" %s values="%s" keyTimes="%s" calcMode="spline" keySplines="%s" dur="%ss" repeatCount="indefinite"/>' % (
        tag, attr, extra, ";".join(str(v) for v in values), ";".join("%.4f" % x for x in KT), ";".join(SP), TOTAL)


def caption_anim(k):
    """단계 문구: 앞 문구가 0.3초 안에 사라진 뒤 새 문구가 나타남"""
    in0, in1 = k * STEP_SEC + 0.40, k * STEP_SEC + MOVE_SEC
    out0, out1 = (k + 1) * STEP_SEC, (k + 1) * STEP_SEC + 0.30
    if k == STEPS - 1:
        pts = [(0, 1), (0.30, 0), (in0, 0), (in1, 1), (TOTAL, 1)]
    else:
        pts = [(0, 0), (in0, 0), (in1, 1), (out0, 1), (out1, 0), (TOTAL, 0)]
    values = ";".join(str(v) for tt, v in pts)
    times = ";".join("%.4f" % (tt / TOTAL) for tt, v in pts)
    return '<animate attributeName="opacity" values="%s" keyTimes="%s" dur="%ss" repeatCount="indefinite"/>' % (values, times, TOTAL)


def svg_defs(t):
    s = "<defs>\n"
    for name, hi, lo in [("steel", t["steel_hi"], t["steel_lo"]), ("green", t["green_hi"], t["green_lo"]), ("red", t["red_hi"], t["red_lo"])]:
        s += '<radialGradient id="face-%s" cx="0.35" cy="0.3" r="0.85"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient>\n' % (name, hi, lo)
        s += ('<linearGradient id="body-%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="0.3" stop-color="%s"/>'
              '<stop offset="1" stop-color="%s"/></linearGradient>\n' % (name, lo, hi, lo))
    s += '<filter id="blur4"><feGaussianBlur stdDeviation="4"/></filter>\n</defs>\n'
    return s


def coil_layer(t, cx, cy, name):
    """옆으로 누운 강판 코일: 뒷면과 몸통, 감긴 줄이 보이는 앞면"""
    fx = cx - BODY / 2
    bx = cx + BODY / 2
    g = ('<path d="M %.1f %.1f L %.1f %.1f A %d %d 0 0 1 %.1f %.1f L %.1f %.1f Z" fill="url(#body-%s)" stroke="%s" stroke-width="1" stroke-opacity="0.6"/>\n'
         % (fx, cy - R, bx, cy - R, FX, R, bx, cy + R, fx, cy + R, name, t["edge"]))
    g += '<path d="M %.1f %.1f L %.1f %.1f" stroke="%s" stroke-opacity="%s" stroke-width="2" stroke-linecap="round"/>\n' % (
        fx + 2, cy - R + 3, bx + 2, cy - R + 3, t["shine"], t["shine_a"])
    g += '<ellipse cx="%.1f" cy="%.1f" rx="%d" ry="%d" fill="url(#face-%s)" stroke="%s" stroke-width="1"/>\n' % (fx, cy, FX, R, name, t["edge"])
    for f in (0.8, 0.62, 0.44):
        g += '<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="none" stroke="%s" stroke-width="1" stroke-opacity="0.5"/>\n' % (
            fx, cy, FX * f, R * f, t["ring"])
    g += '<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" stroke="%s" stroke-width="1" stroke-opacity="0.8"/>\n' % (
        fx, cy, FX * 0.3, R * 0.3, t["hole"], t["ring"])
    return g


def coil(t, i, cx, cy):
    s = "<g>\n"
    s += '<ellipse cx="%d" cy="%d" rx="%d" ry="6" fill="#000" fill-opacity="%s" filter="url(#blur4)"/>\n' % (cx + 6, cy + R + 8, R + 6, t["shadow_a"])
    s += "<g>\n" + animate("transform", lambda k: "0 %d" % (-11 if test_index(k) == i else 0), tag="animateTransform", extra='type="translate"') + "\n"
    s += coil_layer(t, cx, cy, "steel")
    if i < TRAIN_ONLY:
        s += "<g>\n" + coil_layer(t, cx, cy, "green") + "</g>\n"
    else:
        s += '<g opacity="0">\n' + coil_layer(t, cx, cy, "green") + animate("opacity", lambda k: 1 if i < test_index(k) else 0) + "</g>\n"
        s += '<g opacity="0">\n' + coil_layer(t, cx, cy, "red") + animate("opacity", lambda k: 1 if i == test_index(k) else 0) + "</g>\n"
        s += ('<ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="none" stroke="%s" stroke-width="2" opacity="0">' % (cx, cy, BODY / 2 + FX + 9, R + 8, t["red"])
              + animate("opacity", lambda k: 0.45 if i == test_index(k) else 0) + "</ellipse>\n")
    s += "</g>\n"
    lot, date = LOTS[i]
    if i < TRAIN_ONLY:
        s += '<text x="%d" y="%d" font-size="16" font-weight="700" fill="%s" text-anchor="middle">%s</text>\n' % (cx, cy + 60, t["ink"], lot)
    else:
        s += ('<text x="%d" y="%d" font-size="16" font-weight="700" fill="%s" text-anchor="middle">%s' % (cx, cy + 60, t["ink"], lot)
              + animate("fill", lambda k: t["red"] if i == test_index(k) else t["ink"]) + "</text>\n")
    s += '<text x="%d" y="%d" font-size="13" fill="%s" text-anchor="middle">%s</text>\n' % (cx, cy + 79, t["faint"], date)
    return s + "</g>\n"


def walkforward_svg(theme):
    t = SVG_THEMES[theme]
    s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">\n' % (SVG_W, SVG_H, SVG_W, SVG_H, FONT)
    s += "<title>앞 4개 LOT으로 배우고 다음 LOT 하나를 시험하는 과정을 10번 반복</title>\n" + svg_defs(t)
    s += '<rect x="0.5" y="0.5" width="%d" height="%d" rx="16" fill="%s" stroke="%s"/>\n' % (SVG_W - 1, SVG_H - 1, t["card"], t["stroke"])
    s += '<text x="40" y="50" font-size="21" font-weight="700" fill="%s">시간 순서를 지키는 시험</text>\n' % t["ink"]
    s += '<text x="40" y="77" font-size="15" fill="%s">앞 LOT으로 배우고, 바로 다음 LOT 하나를 맞힘 · 10번 반복</text>\n' % t["sub"]
    for k in range(STEPS):
        lot = LOTS[test_index(k)][0]
        s += ('<g opacity="0"><text x="%d" y="50" font-size="21" font-weight="700" fill="%s" text-anchor="end">시험 <tspan fill="%s">%d</tspan> / %d</text>'
              '<text x="%d" y="77" font-size="15" fill="%s" text-anchor="end">앞의 %d개 LOT으로 배우고 LOT %s를 맞힘</text>'
              % (SVG_W - 40, t["ink"], t["red"], k + 1, STEPS, SVG_W - 40, t["sub"], test_index(k), lot) + caption_anim(k) + "</g>\n")
    for i in range(len(LOTS)):
        s += coil(t, i, X0 + i * PITCH, CY)
    by = CY + 104
    left = X0 - R
    s += '<rect x="%d" y="%d" width="%d" height="6" rx="3" fill="%s" fill-opacity="0.18"/>\n' % (left, by, (len(LOTS) - 1) * PITCH + 2 * R, t["faint"])
    s += ('<rect x="%d" y="%d" width="%d" height="6" rx="3" fill="%s">' % (left, by, (TRAIN_ONLY - 1) * PITCH + 2 * R + 4, t["green"])
          + animate("width", lambda k: (test_index(k) - 1) * PITCH + 2 * R + 4) + "</rect>\n")
    chip_w = 50
    s += ('<g transform="translate(%d 0)">' % (X0 + TRAIN_ONLY * PITCH - chip_w // 2)
          + animate("transform", lambda k: "%d 0" % (X0 + test_index(k) * PITCH - chip_w // 2), tag="animateTransform", extra='type="translate"') + "\n"
          '<rect x="0" y="%d" width="%d" height="24" rx="12" fill="%s"/>\n'
          '<text x="%d" y="%d" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">시험</text></g>\n'
          % (by + 14, chip_w, t["red"], chip_w // 2, by + 31))
    ly = SVG_H - 26
    lx = 40
    for label, col in [("학습에 씀", t["green"]), ("지금 시험하는 LOT", t["red"]), ("아직 안 본 미래", t["steel_lo"])]:
        s += '<circle cx="%d" cy="%d" r="6.5" fill="%s"/>\n' % (lx + 6, ly - 5, col)
        s += '<text x="%d" y="%d" font-size="14" fill="%s">%s</text>\n' % (lx + 21, ly, t["sub"], label)
        lx += 21 + len(label) * 14 + 30
    s += '<text x="%d" y="%d" font-size="14" fill="%s" text-anchor="end">10번 결과를 합쳐 F1 · 미래 값은 쓰지 않음 · random_state = 42</text>\n' % (SVG_W - 40, ly, t["faint"])
    return s + "</svg>\n"


def build_svg():
    for theme in SVG_THEMES:
        path = os.path.join(HERE, "walkforward-%s.svg" % theme)
        open(path, "w", encoding="utf-8", newline="\n").write(walkforward_svg(theme))
        print(path, round(os.path.getsize(path) / 1024, 1), "KB")


# ---------------------------------------------------------------- 2. 히어로 (WebP)
HERO_W, HERO_H = 1600, 600        # 합성 크기 (저장할 때 1440x540으로 줄임)
HERO_FPS = 20
CLIP_SEC = 3.6                    # 녹화 0 ~ 3.6초: 금속 설비 → 홀로그램
CROP = (455, 96, 1760, 850)       # 녹화에서 3D 영역 (왼쪽 패널과 아래 버튼 바깥)
BG = (11, 17, 28)                 # 녹화 바탕에 맞춘 색
PAINT = [(1145, 0, 1305, 140)]    # 지울 UI (오른쪽 위 버튼과 말풍선), CROP 기준
NODES = [("CLN", (96, 165, 250)), ("Z1", (125, 190, 255)), ("Z2", (125, 190, 255)),
         ("Z3", (255, 122, 69)), ("Z4", (255, 92, 72)), ("Z5", (255, 122, 69)), ("Z6", (255, 138, 76)),
         ("Z7", (255, 177, 92)), ("Z8", (255, 177, 92)), ("Z9", (255, 190, 120)), ("OUT", (140, 190, 230))]
LINE_X0, LINE_X1, LINE_Y = 84, 640, 520


def node_x(i):
    return LINE_X0 + (LINE_X1 - LINE_X0) * i / (len(NODES) - 1)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def edge_screenshot(html_path, png_path, width, height, transparent=True):
    if os.path.exists(png_path):
        os.remove(png_path)
    args = [EDGE, "--headless", "--disable-gpu", "--no-first-run", "--user-data-dir=" + os.path.join(WORK, "edge"), "--hide-scrollbars",
            "--window-size=%d,%d" % (width, height), "--screenshot=" + png_path, "file:///" + html_path.replace("\\", "/")]
    if transparent:
        args.insert(1, "--default-background-color=00000000")
    subprocess.run(args, capture_output=True, timeout=120)
    for step in range(60):  # Edge가 파일을 다 쓸 때까지 기다림
        if os.path.exists(png_path) and os.path.getsize(png_path) > 1000:
            break
        time.sleep(0.5)


def hero_overlay(path_png):
    nodes = ""
    for i in range(len(NODES)):
        label, col = NODES[i]
        x = node_x(i)
        nodes += '<div class="node" style="left:%.1fpx;background:rgb(%d,%d,%d);box-shadow:0 0 0 4px rgba(%d,%d,%d,.16)"></div>' % (
            x, col[0], col[1], col[2], col[0], col[1], col[2])
        nodes += '<div class="nl" style="left:%.1fpx">%s</div>' % (x, label)
    html = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}
.wrap{position:relative;width:%(W)dpx;height:%(H)dpx;overflow:hidden;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;color:#eef3fa}
.eyebrow{position:absolute;left:84px;top:66px;font-size:16px;letter-spacing:.34em;font-weight:500;color:#5eead4;display:flex;align-items:center}
.eyebrow:before{content:"";display:block;width:34px;height:1px;background:#5eead4;margin-right:16px;opacity:.85}
h1{position:absolute;left:82px;top:100px;margin:0;font-size:54px;line-height:1.22;font-weight:700;letter-spacing:-.025em}
h1 span{display:block}
h1 .l1{color:#f4f7fb}
h1 .l2{background:linear-gradient(90deg,#5eead4 0%%,#7dd3fc 72%%,#a5b4fc 100%%);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{position:absolute;left:86px;top:254px;font-size:22px;line-height:1.45;color:#a3b3c8;letter-spacing:-.01em}
.spec{position:absolute;left:86px;top:348px;display:grid;grid-template-columns:76px auto;row-gap:10px;font-size:19px}
.spec .k{color:#71859c;font-weight:500}
.spec .v{color:#dbe5f2}
.spec .v b{color:#fff;font-weight:700}
.line{position:absolute;left:%(LX0)dpx;top:%(LY)dpx;width:%(LW)dpx;height:2px;border-radius:2px;opacity:.55;
background:linear-gradient(90deg,#60a5fa 0%%,#7dbeff 18%%,#ff7a45 30%%,#ff5c48 42%%,#ff8a4c 62%%,#ffb15c 74%%,#ffbe78 90%%,#8cbee6 100%%)}
.node{position:absolute;top:%(NY)spx;width:10px;height:10px;margin-left:-5px;border-radius:50%%}
.nl{position:absolute;top:%(LY2)dpx;width:60px;margin-left:-30px;text-align:center;font-family:'Segoe UI','Noto Sans KR',sans-serif;font-size:15px;letter-spacing:.06em;color:#8496ab}
</style></head><body><div class="wrap">
<div class="eyebrow">CAL01 PREDICTIVE MAINTENANCE</div>
<h1><span class="l1">연속 소둔로의 흐름을 보고,</span><span class="l2">같은 구간을 팀이 함께 판단함</span></h1>
<div class="sub">3σ 통계 후보 → 팀 판단 → 규칙으로 정답을 다듬고,<br>시간 순서를 지켜 모델을 시험함</div>
<div class="spec">
<div class="k">데이터</div><div class="v"><b>14</b> LOT · <b>345,390</b> 원기록 · <b>21</b> 센서</div>
<div class="k">정답</div><div class="v">팀 판단 <b>33</b>건 · 전 구역 검토 <b>81</b>건 · 규칙 <b>2</b>개</div>
<div class="k">성능</div><div class="v">Z4 F1 <b>0.60</b> Z-score · <b>0.59</b> RandomForest</div>
</div>
<div class="line"></div>%(NODES)s
</div></body></html>""" % dict(W=HERO_W, H=HERO_H, LX0=LINE_X0, LY=LINE_Y, LW=LINE_X1 - LINE_X0, NY="%.1f" % (LINE_Y - 4), LY2=LINE_Y + 14, NODES=nodes)
    html_path = os.path.join(WORK, "hero_overlay.html")
    open(html_path, "w", encoding="utf-8").write(html)
    edge_screenshot(html_path, path_png, HERO_W, HERO_H)


def ease(u):
    return u * u * (3 - 2 * u)


def build_hero():
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    raw = os.path.join(WORK, "hero_raw")
    os.makedirs(raw, exist_ok=True)
    for f in glob.glob(os.path.join(raw, "*.png")):
        os.remove(f)
    x0, y0, x1, y1 = CROP
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-ss", "0", "-t", str(CLIP_SEC), "-i", SCENE_MP4, "-r", str(HERO_FPS),
                    "-vf", "crop=%d:%d:%d:%d" % (x1 - x0, y1 - y0, x0, y0), os.path.join(raw, "%03d.png")], check=True)
    files = sorted(glob.glob(os.path.join(raw, "*.png")))
    overlay_png = os.path.join(WORK, "hero_overlay.png")
    hero_overlay(overlay_png)
    ov = Image.open(overlay_png).convert("RGBA")
    # 앞으로 재생한 뒤 거꾸로 돌아옴: 금속 설비 → 홀로그램 → 금속 설비 (반복 이음새가 없음)
    order = list(range(len(files))) + list(range(len(files) - 2, 0, -1))
    cw, ch = Image.open(files[0]).size   # ffmpeg가 홀수 크기를 줄일 수 있어 실제 크기를 씀
    scale = 0.72
    win_w, win_h = int(cw * scale), int(ch * scale)
    win_x, win_y = HERO_W - win_w - 10, 38
    mask = Image.new("L", (win_w, win_h), 255)
    md = ImageDraw.Draw(mask)
    fade = 340
    for x in range(fade):
        md.line((x, 0, x, win_h), fill=int(255 * ease(x / fade) ** 1.5))
    edge = Image.new("L", (win_w, win_h), 0)
    ImageDraw.Draw(edge).rectangle((26, 26, win_w - 10, win_h - 26), fill=255)
    mask = ImageChops.multiply(mask, edge.filter(ImageFilter.GaussianBlur(22)))
    base = Image.new("RGB", (HERO_W, HERO_H), BG)
    glow = Image.new("RGB", (HERO_W, HERO_H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((win_x + win_w * 0.18, win_y + win_h * 0.05, win_x + win_w * 1.0, win_y + win_h * 1.08), fill=(14, 52, 64))
    base = ImageChops.add(base, glow.filter(ImageFilter.GaussianBlur(120)))
    frames = []
    total = len(order)
    for k in range(total):
        fr = Image.open(files[order[k]]).convert("RGB")
        for (px0, py0, px1, py1) in PAINT:
            pm = Image.new("L", fr.size, 0)
            ImageDraw.Draw(pm).rectangle((px0, py0, px1, py1), fill=255)
            fr = Image.composite(Image.new("RGB", fr.size, BG), fr, pm.filter(ImageFilter.GaussianBlur(14)))
        phase = k / total
        zoom = 1.0 + 0.055 * (0.5 - 0.5 * math.cos(2 * math.pi * phase))   # 천천히 다가갔다 물러남
        zw, zh = cw / zoom, ch / zoom
        cx = cw * 0.5 + 18 * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
        left = min(max(cx - zw / 2, 0), cw - zw)
        top = min(max(ch * 0.5 - zh / 2, 0), ch - zh)
        box = (max(0.0, left), max(0.0, top), min(float(cw), left + zw), min(float(ch), top + zh))
        canvas = base.copy()
        canvas.paste(fr.resize((win_w, win_h), Image.LANCZOS, box=box), (win_x, win_y), mask)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), ov)
        # 공정선을 따라 흐르는 빛
        lead = LINE_X0 + (LINE_X1 - LINE_X0) * min(1.0, max(0.0, (phase - 0.04) / 0.92))
        alpha = 1.0 if 0.04 < phase < 0.96 else 0.0
        layer = Image.new("RGBA", (HERO_W, HERO_H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for i in range(len(NODES)):
            col = NODES[i][1]
            a = max(0.0, 1.0 - abs(node_x(i) - lead) / 60.0) * alpha
            if a > 0.01:
                rr = 5 + 9 * a
                ld.ellipse((node_x(i) - rr, LINE_Y + 1 - rr, node_x(i) + rr, LINE_Y + 1 + rr), fill=(col[0], col[1], col[2], int(150 * a)))
        ld.ellipse((lead - 4, LINE_Y - 3, lead + 4, LINE_Y + 5), fill=(255, 255, 255, int(235 * alpha)))
        canvas = Image.alpha_composite(canvas, layer.filter(ImageFilter.GaussianBlur(7)))
        canvas = Image.alpha_composite(canvas, layer)
        frames.append(canvas.convert("RGB").resize((1440, 540), Image.LANCZOS))
    out = os.path.join(HERE, "hero.webp")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / HERO_FPS), loop=0, quality=74, method=4)
    print(out, len(frames), "프레임", round(os.path.getsize(out) / 1e6, 2), "MB")


# ---------------------------------------------------------------- 3. 관제 화면 (WebP)
def build_monitor():
    from PIL import Image
    d = os.path.join(WORK, "monitor_raw")
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, "*.png")):
        os.remove(f)
    fps = 10
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-ss", "0", "-t", "16", "-i", SCENE_MP4, "-r", str(fps),
                    "-vf", "scale=960:540:flags=lanczos", os.path.join(d, "%04d.png")], check=True)
    frames = [Image.open(f).convert("RGB") for f in sorted(glob.glob(os.path.join(d, "*.png")))]
    n = int(0.6 * fps)   # 끝 0.6초를 첫 화면과 겹쳐 반복 이음새를 부드럽게
    for i in range(n):
        frames[len(frames) - n + i] = Image.blend(frames[len(frames) - n + i], frames[0], (i + 1) / (n + 1))
    out = os.path.join(HERE, "monitor.webp")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, quality=76, method=4)
    print(out, len(frames), "프레임", round(os.path.getsize(out) / 1e6, 2), "MB")


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    job = sys.argv[1] if len(sys.argv) > 1 else "svg"
    if job == "svg":
        build_svg()
    elif job == "hero":
        build_hero()
    elif job == "monitor":
        build_monitor()
