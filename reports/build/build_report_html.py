# 결과보고서 Markdown(reports/결과보고서.md)을 시계열 분석 보고서와 같은 양식의 HTML로 만들고,
# Edge(헤드리스)로 PDF를 뽑은 뒤 쪽마다 상단 장 탭·경로줄·꼬리말·쪽 번호를 덧그림
# 실행 (pdm-project 폴더에서): uv run --with pymupdf python reports/build/build_report_html.py
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # pdm-project
ASSETS = os.path.join(HERE, "assets")
MD = os.path.join(ROOT, "reports", "결과보고서.md")
HTML_OUT = os.path.join(ROOT, "reports", "결과보고서.html")
PDF_OUT = os.path.join(ROOT, "reports", "CAL01_소둔로 이상 탐지 결과보고서(3조 오운완).pdf")  # 시계열 분석 보고서 파일명과 같은 형식
EDGE = os.environ.get("EDGE_EXE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
FONT_FILE = r"C:\Windows\Fonts\NotoSansKR-VF.ttf"
FONT_FALLBACK = r"C:\Windows\Fonts\malgun.ttf"

# 양식 색 (시계열 분석 보고서 PDF에서 읽은 값)
BLUE = (0x00 / 255, 0x5f / 255, 0x98 / 255)
BLUE_BAR = (0x00 / 255, 0x5e / 255, 0x97 / 255)
BLUE_MID = (0x57 / 255, 0x93 / 255, 0xbd / 255)
PILL = (0xd6 / 255, 0xe6 / 255, 0xf2 / 255)
HEAD_BG = (0xf0 / 255, 0xf6 / 255, 0xfb / 255)
GRAY = (0x60 / 255, 0x6a / 255, 0x73 / 255)
RULE = (0xcf / 255, 0xd4 / 255, 0xd8 / 255)
PAGE_NO = (0x58 / 255, 0x94 / 255, 0xbe / 255)
WHITE = (1, 1, 1)

FOOTER_TEXT = "CAL01 | 연속소둔로 이상 탐지 결과보고서"

# 표지와 목차 내용
COVER = {
    "eyebrow": "CONTINUOUS ANNEALING LINE",
    "title": ["2024", "CAL01", "ANOMALY", "DETECTION"],
    "subtitle": "Z-score baseline, team labels and RandomForest",
    "subline": "연속소둔로 이상 탐지 결과보고서 · 정답 정의 v1~v7 · 모델 평가 · 오탐 미탐 사례 분석",
    "rows": [
        ("대상 설비", "P1-CR1-CAL01  연속소둔로"),
        ("관측 기간", "2024-01-02 ~ 2024-12-28  |  14개 LOT · 5,938분"),
        ("자료 성격", "교육용 재현 데이터 · 실제 현장 실증 아님"),
        ("부서·팀명", "소둔공정 데이터 분석  |  오운완"),
        ("팀원", "김태구 · 김정렬 · 정수진 · 박민호 · 황유진"),
        ("작성자", "박민호  |  2026. 10. 25.  (초안)"),
        ("저장소", "github.com/posco-3bungi-pdm/pdm-project"),
    ],
}
CHAPTERS = [
    # (탭 이름, 목차 부제)
    ("문제 정의", "대상 설비 · 이상 정의 · 성공 기준"),
    ("데이터", "출처 · 기간 · 변수 · 품질 이슈"),
    ("전처리", "1분 묶음 · 제외 구간 · 통계 후보"),
    ("시계열", "공통 움직임과 CP 단독 튐"),
    ("모델링", "분할 · 정답 v1~v7 · 기준 모델 · RF · 2단계"),
    ("평가", "성능 표 · 혼동행렬 · LOT별 · 오탐 미탐 사례"),
    ("보전 해석", "정비 이력 연결 · 활용 시나리오 · 임곗값"),
    ("한계", "판단하지 못하는 것 · 다음 데이터"),
    ("역할", "팀원별 담당 · 배운 점"),
]
CSS = """
@page { size: A4; margin: 35mm 15.9mm 17mm 15.9mm; }
@page :first { margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Noto Sans KR", "Malgun Gothic", sans-serif; font-size: 9.1pt; color: #333; line-height: 1.5; font-weight: 400; }
a { color: #005f98; text-decoration: none; }
code { font-family: Consolas, "Noto Sans KR", monospace; font-size: 8.4pt; color: #50545a; background: #f0f6fb; padding: 0 3pt; border-radius: 2pt; }
p { margin: 0 0 5pt 0; }
b { font-weight: 700; }

/* 표지 */
.cover { width: 210mm; height: 297mm; position: relative; background: #eff8fb; page-break-after: always; overflow: hidden; }
.cover .eyebrow { position: absolute; left: 18mm; top: 30mm; font-size: 8.8pt; font-weight: 700; color: #005f98; letter-spacing: 0.4pt; }
.cover .logos { position: absolute; right: 16mm; top: 22mm; display: flex; gap: 8mm; align-items: center; }
.cover .logos img { height: 11mm; }
.cover .title { position: absolute; left: 18mm; top: 42mm; font-size: 47pt; font-weight: 700; color: #005f98; line-height: 1.08; letter-spacing: -0.5pt; }
.cover .subtitle { position: absolute; left: 18mm; top: 124mm; font-size: 14.5pt; font-weight: 700; color: #50545a; }
.cover .subline { position: absolute; left: 18mm; top: 133mm; font-size: 9.2pt; color: #333; }
.cover .band { position: absolute; left: 0; right: 0; bottom: 0; height: 106.5mm; background: #cddbeb; }
.cover .rows { position: absolute; left: 18mm; bottom: 20mm; }
.cover .rows div { display: flex; margin: 0 0 4.2mm 0; font-size: 8.6pt; }
.cover .rows span.k { width: 18mm; color: #606a73; }
.cover .rows span.v { color: #005f98; }

/* 목차 */
.toc-title { font-size: 25pt; font-weight: 500; color: #005f98; margin: 2mm 0 2mm 0; }
.toc-flow { font-size: 10pt; color: #606a73; margin: 0 0 6mm 0; }
.toc-row { display: flex; align-items: flex-start; height: 50pt; padding: 8pt 9mm 0 9mm; border-radius: 3.5mm; margin-bottom: 13pt; }
.toc-row:nth-child(odd) { background: #edf4f9; }
.toc-row .no { width: 34pt; font-size: 16pt; font-weight: 700; color: #5894be; line-height: 1.2; }
.toc-row .t { flex: 1; }
.toc-row .t .name { font-size: 12pt; font-weight: 500; color: #005f98; line-height: 1.25; }
.toc-row .t .sub { font-size: 8.8pt; color: #606a73; margin-top: 2pt; }
.toc-row .pg { width: 10mm; text-align: right; font-size: 11pt; color: #333; }
.toc-note { font-size: 8.2pt; color: #606a73; margin: 3mm 0 0 0; }
.contact { margin-top: 5mm; }

/* 장·절 */
.chapter { margin-top: 5mm; }
.chapter.first { page-break-before: always; margin-top: 0; }
.chapter-bar { background: #005e97; color: #fff; font-size: 10pt; font-weight: 500; padding: 4pt 12pt; border-radius: 2pt; margin: 0 0 4mm 0; page-break-after: avoid; break-after: avoid; }
.chapter-bar span { margin-left: 10pt; }
.sec { display: flex; align-items: center; margin: 4.5mm 0 1mm 0; page-break-after: avoid; }
.sec .badge { width: 47pt; height: 29pt; border-radius: 4pt; background: #e9f2f9; color: #005f98; font-size: 14pt; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-right: 12pt; }
.sec .name { font-size: 16.5pt; font-weight: 500; color: #333; }
.sec-label { font-size: 8.1pt; color: #5894be; margin: 0 0 2mm 0; break-after: avoid; page-break-after: avoid; }
h4 { font-size: 10.4pt; font-weight: 500; color: #005f98; margin: 3.5mm 0 1.5mm 0; page-break-after: avoid; }

/* 상자 */
.callout { background: #f0f6fb; border-left: 3pt solid #5793bd; padding: 5pt 10pt; margin: 2mm 0 3mm 0; font-size: 9.3pt; page-break-inside: avoid; }
.callout.key { background: #e9f4f9; border-left: none; color: #005f98; border-radius: 2pt; }
.note { background: #f3f5f7; color: #606a73; font-size: 8.6pt; padding: 5pt 10pt; border-radius: 2pt; margin: 0 0 4mm 0; }

/* 목록 */
ul { margin: 0 0 3mm 0; padding-left: 14pt; }
li { margin: 0 0 1.5pt 0; }
ul ul { margin: 1.5pt 0 1.5pt 0; }
li::marker { color: #5894be; }
.tag { font-weight: 700; font-size: 8.6pt; }
.t-fact { color: #005f98; } .t-team { color: #5894be; } .t-hyp { color: #606a73; }

/* 표 */
.tcap { font-size: 8.1pt; color: #005f98; font-weight: 500; margin: 2.5mm 0 1.2mm 0; page-break-after: avoid; break-after: avoid; }
table.data { width: 100%; border-collapse: collapse; margin: 0 0 3mm 0; font-size: 7.9pt; page-break-inside: avoid; }
table.data th { background: #5793bd; color: #fff; font-weight: 500; text-align: left; padding: 3pt 6pt; font-size: 8pt; }
table.data th, table.data td { border-bottom: 0.35pt solid #cfd4d8; }
table.data th + th, table.data td + td { border-left: 0.3pt solid #cfd4d8; }
table.data td { padding: 2.6pt 6pt; vertical-align: top; line-height: 1.4; }
table.data td:first-child { background: #cadbe9; color: #005f98; }
table.data.plain td:first-child { background: transparent; color: #333; }
table.data.nw td:first-child, table.data.nw th:first-child { white-space: nowrap; }
table.data.long { page-break-inside: auto; }
table.data.long tr { page-break-inside: avoid; }
table.data thead { display: table-header-group; }
.keep { page-break-inside: avoid; }

/* 그림 */
figure { margin: 1.5mm 0 3.5mm 0; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; }
figcaption { font-size: 8.1pt; color: #606a73; margin-top: 2mm; text-align: left; }
figcaption b { color: #005f98; font-weight: 500; }
"""

INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[사실\]|\[팀 해석\]|\[가설\]|https?://[^\s)]+)")
TAG_CLASS = {"[사실]": "t-fact", "[팀 해석]": "t-team", "[가설]": "t-hyp"}


def inline(text):
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append("<b>" + inline(part[2:-2]) + "</b>")
        elif part.startswith("`") and part.endswith("`"):
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
        elif part in TAG_CLASS:
            out.append('<span class="tag %s">%s</span>' % (TAG_CLASS[part], part))
        elif part.startswith("http"):
            out.append('<a href="%s">%s</a>' % (html.escape(part), html.escape(part)))
        else:
            out.append(html.escape(part.replace("\\|", "|")))
    return "".join(out)


SPLIT_CELL = re.compile(r"(?<!\\)\|")


def split_row(line):
    cells = SPLIT_CELL.split(line.strip())
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def parse(md_lines):
    """md를 장 목록으로. 장 = {"num", "title", "blocks"}; 블록 = (종류, 값)"""
    chapters = []
    cur = None
    pending_caption = None
    i = 0
    first_table_skipped = False
    while i < len(md_lines):
        line = md_lines[i]
        s = line.strip()
        if not s or s == "\\newpage":
            i += 1
            continue
        if s.startswith("# ") and not s.startswith("## "):
            i += 1
            continue
        if s.startswith("## "):
            m = re.match(r"^## (\d+)\.\s*(.*)$", s)
            cur = {"num": int(m.group(1)), "title": m.group(2).strip(), "blocks": []}
            chapters.append(cur)
            i += 1
            continue
        if cur is None:  # 표지 앞 머리말 (읽는 법)은 목차 쪽으로
            cur = {"num": 0, "title": "머리말", "blocks": []}
            chapters.append(cur)
        if s.startswith("### "):
            m = re.match(r"^### (\d+)\.(\d+)\s*(.*)$", s)
            cur["blocks"].append(("section", (m.group(1), m.group(2), m.group(3).strip())))
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(md_lines) and md_lines[i].strip().startswith("|"):
                r = split_row(md_lines[i])
                if not all(re.fullmatch(r":?-+:?", c) for c in r):
                    rows.append(r)
                i += 1
            if not first_table_skipped:
                first_table_skipped = True  # 문서 정보 표는 표지가 대신함
                continue
            cur["blocks"].append(("table", (pending_caption, rows)))
            pending_caption = None
            continue
        m = re.match(r"^!\[(.*)\]\((.*)\)$", s)
        if m:
            cur["blocks"].append(("image", (m.group(1), m.group(2))))
            i += 1
            continue
        if re.match(r"^표 [\d\-]+\.", s):
            pending_caption = s
            i += 1
            continue
        if re.match(r"^\s*- ", line):
            items = []
            while i < len(md_lines) and re.match(r"^\s*- ", md_lines[i]):
                m2 = re.match(r"^(\s*)- (.*)$", md_lines[i])
                items.append((1 if len(m2.group(1)) >= 2 else 0, m2.group(2)))
                i += 1
            cur["blocks"].append(("bullets", items))
            continue
        if s.startswith("**") and s.endswith("**"):
            cur["blocks"].append(("subhead", s[2:-2]))
            i += 1
            continue
        if s.startswith("(") and s.endswith(")"):
            cur["blocks"].append(("note", s))
            i += 1
            continue
        cur["blocks"].append(("para", s))
        i += 1
    return chapters


def render_bullets(items, key=False):
    out = []
    if key:
        for _, t in items:
            out.append('<div class="callout key">%s</div>' % inline(t))
        return "".join(out)
    out.append("<ul>")
    open_sub = False
    for level, t in items:
        if level == 1 and not open_sub:
            out.append("<ul>")
            open_sub = True
        if level == 0 and open_sub:
            out.append("</ul>")
            open_sub = False
        out.append("<li>%s</li>" % inline(t))
    if open_sub:
        out.append("</ul>")
    out.append("</ul>")
    return "".join(out)


def render_table(caption, rows, plain=False):
    out = []
    if caption:
        m = re.match(r"^(표 [\d\-]+\.)\s*(.*)$", caption)
        out.append('<div class="tcap">%s %s</div>' % (m.group(1), inline(m.group(2))))
    short_first = all(len(re.sub(r"[`*]", "", r[0])) <= 9 for r in rows if r)
    long = len(rows) > 10  # 긴 표는 쪽을 넘기되 머리글을 반복
    out.append('<table class="data%s%s%s">' % (" plain" if plain else "", " nw" if short_first else "", " long" if long else ""))
    out.append("<thead><tr>" + "".join("<th>%s</th>" % inline(c) for c in rows[0]) + "</tr></thead><tbody>")
    for r in rows[1:]:
        out.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def render_image(cap, path):
    full = os.path.join(ROOT, path)
    width = 100
    mw = re.search(r"\s*\{w=(\d+)\}\s*$", cap)  # 알트 끝의 {w=60}은 그림 폭(%)
    if mw:
        width = int(mw.group(1))
        cap = cap[: mw.start()]
    m = re.match(r"^((?:그림) [\d\-]+\.)\s*(.*)$", cap)
    label = "<b>%s</b> %s" % (m.group(1), inline(m.group(2))) if m else inline(cap)
    return '<figure><img src="%s" style="width:%d%%"><figcaption>%s</figcaption></figure>' % (
        html.escape(pathlib.Path(full).as_uri()), width, label)


def render_chapter(ch, toc_pages):
    out = ['<div class="chapter%s" id="ch%d">' % (" first" if ch["num"] == 1 else "", ch["num"])]
    out.append('<div class="chapter-bar">CHAPTER %02d<span>%s</span></div>' % (ch["num"], html.escape(ch["title"])))
    key_mode = False
    head = ""  # 절 제목은 첫 내용과 한 묶음으로 두어 쪽 끝에 혼자 남지 않게 함
    for kind, val in ch["blocks"]:
        if kind == "section":
            _, sub, title = val
            key_mode = "종합" in title
            head = ('<div class="sec"><div class="badge">%02d</div><div class="name">%s</div></div>' % (int(sub), html.escape(title))
                    + '<div class="sec-label">%s · %s.%s</div>' % (html.escape(ch["title"]), ch["num"], sub))
            continue
        if kind == "table":
            block = render_table(*val)
        elif kind == "image":
            block = render_image(*val)
        elif kind == "bullets":
            block = render_bullets(val, key=key_mode)
        elif kind == "subhead":
            block = "<h4>%s</h4>" % inline(val)
        elif kind == "note":
            block = '<div class="note">%s</div>' % inline(val)
        else:
            block = "<p>%s</p>" % inline(val)
        small = kind in ("para", "note", "subhead") or (kind == "bullets" and len(val) <= 3) or (kind == "table" and len(val[1]) <= 5)
        if head and small:
            out.append('<div class="keep">' + head + block + "</div>")
            head = ""
        elif head:
            out.append(head + block)  # 큰 블록은 CSS break-after: avoid에 맡김
            head = ""
        else:
            out.append(block)
    if head:
        out.append(head)
    out.append("</div>")
    return "".join(out)


def render_cover():
    rows = "".join('<div><span class="k">%s</span><span class="v">%s</span></div>' % (html.escape(k), html.escape(v)) for k, v in COVER["rows"])
    logos = ""
    for name in ("KNDA.svg", "POSCO.svg"):
        p = os.path.join(ASSETS, name)
        if os.path.exists(p):
            logos += '<img src="%s">' % html.escape(pathlib.Path(p).as_uri())
    return (
        '<div class="cover">'
        '<div class="eyebrow">%s</div>'
        '<div class="logos">%s</div>'
        '<div class="title">%s</div>'
        '<div class="subtitle">%s</div>'
        '<div class="subline">%s</div>'
        '<div class="band"></div>'
        '<div class="rows">%s</div>'
        "</div>" % (COVER["eyebrow"], logos, "<br>".join(COVER["title"]), html.escape(COVER["subtitle"]), html.escape(COVER["subline"]), rows)
    )


def render_toc(chapters, toc_pages, preface):
    out = ['<div id="toc">', '<div class="toc-title">목차</div>',
           '<div class="toc-flow">보고서 흐름 · 문제 정의 → 데이터와 전처리 → 시계열 분석 → 모델링 → 평가와 오류 분석 → 보전 관점 해석 → 한계와 역할</div>']
    for ch in chapters:
        if ch["num"] == 0:
            continue
        tab, sub = CHAPTERS[ch["num"] - 1]
        pg = toc_pages.get(ch["num"], "")
        out.append('<a class="toc-row" href="#ch%d"><div class="no">%02d</div><div class="t"><div class="name">%s</div><div class="sub">%s</div></div><div class="pg">%s</div></a>'
                   % (ch["num"], ch["num"], html.escape(ch["title"]), html.escape(sub), pg))
    out.append('<div class="toc-note">상단 장 이름 또는 목차 항목을 누르면 해당 장으로 이동한다.</div>')
    out.append("</div>")
    return "".join(out)


def build_html(chapters, toc_pages):
    preface = next((c for c in chapters if c["num"] == 0), None)
    body = render_cover() + render_toc(chapters, toc_pages, preface)
    for ch in chapters:
        if ch["num"] == 0:
            continue
        body += render_chapter(ch, toc_pages)
    doc = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>CAL01 연속 소둔로 이상 탐지 결과보고서</title><style>%s</style></head><body>%s</body></html>' % (CSS, body)
    open(HTML_OUT, "w", encoding="utf-8").write(doc)


def print_pdf(pdf_path):
    profile = os.path.join(tempfile.gettempdir(), "edge_profile_report")
    url = pathlib.Path(HTML_OUT).as_uri()
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + profile,
           "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=6000",
           "--print-to-pdf=" + pdf_path, url]
    subprocess.run(cmd, check=False, capture_output=True, timeout=120)
    if not os.path.exists(pdf_path):
        raise SystemExit("Edge가 PDF를 만들지 못함: " + pdf_path)


def chapter_pages(pdf_path):
    """각 장이 시작하는 쪽 번호 (1부터)"""
    doc = fitz.open(pdf_path)
    found = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        for m in re.finditer(r"CHAPTER (\d{2})", text):
            n = int(m.group(1))
            if n not in found:
                found[n] = i + 1
    return found


def stamp(pdf_path, out_path, chapters):
    doc = fitz.open(pdf_path)
    font_file = FONT_FILE if os.path.exists(FONT_FILE) else FONT_FALLBACK
    try:
        font = fitz.Font(fontfile=font_file)
    except Exception:
        font_file = FONT_FALLBACK
        font = fitz.Font(fontfile=font_file)
    sections = []  # (장 번호, 절 이름) 문서 순서
    for ch in chapters:
        for kind, val in ch["blocks"]:
            if kind == "section":
                sections.append((ch["num"], val[2]))
    titles = {ch["num"]: ch["title"] for ch in chapters}
    cur_ch = 0
    cur_sec = "목차"
    width = doc[0].rect.width
    x0, x1 = 45.0, 550.0  # 원본 본문 폭 505pt
    n_tabs = len(CHAPTERS)
    gap = 5.0
    pill_w = (x1 - x0 - gap * (n_tabs - 1)) / n_tabs
    ch_pages = chapter_pages(pdf_path)
    for i, page in enumerate(doc):
        if i == 0:
            continue
        text = page.get_text()
        flat = re.sub(r"\s+", " ", text)
        m = re.search(r"CHAPTER (\d{2})", text)
        if m:
            cur_ch = int(m.group(1))
            cur_sec = ""
        # 경로줄에는 이 쪽의 첫 절을, 다음 쪽으로는 이 쪽의 마지막 절을 넘김
        found = []
        for chn, name in sections:
            if chn != cur_ch:
                continue
            hits = page.search_for(name)
            if hits:
                found.append((min(r.y0 for r in hits), name))
        if found:
            found.sort()
            page_sec = found[0][1]
            cur_sec = found[-1][1]
        else:
            page_sec = cur_sec
        if i == 1:
            cur_ch = 0
            cur_sec = page_sec = "목차"
        shape = page.new_shape()
        # 머리띠
        shape.draw_rect(fitz.Rect(0, 0, width, 66))
        shape.finish(color=None, fill=HEAD_BG)
        shape.draw_rect(fitz.Rect(0, 65, width, 67))
        shape.finish(color=None, fill=BLUE_MID)
        # 장 탭
        for k, (tab, _) in enumerate(CHAPTERS):
            rx0 = x0 + k * (pill_w + gap)
            r = fitz.Rect(rx0, 25, rx0 + pill_w, 45)
            active = (k + 1) == cur_ch
            shape.draw_rect(r, radius=0.5)  # 알약 모양
            shape.finish(color=None, fill=BLUE_BAR if active else PILL)
            tw = font.text_length(tab, fontsize=8)
            shape.insert_text(fitz.Point(rx0 + (pill_w - tw) / 2, 38.3), tab, fontsize=8, fontname="NotoKR", fontfile=font_file, color=WHITE if active else BLUE)
            if (k + 1) in ch_pages:
                page.insert_link({"kind": fitz.LINK_GOTO, "from": r, "page": ch_pages[k + 1] - 1, "to": fitz.Point(0, 0)})
        # 경로줄
        if not cur_ch:
            crumb = "개요  /  목차"
        elif page_sec:
            crumb = "%s  /  %s" % (titles.get(cur_ch, ""), page_sec)
        else:
            crumb = titles.get(cur_ch, "")
        shape.insert_text(fitz.Point(x0, 81.5), crumb, fontsize=8, fontname="NotoKR", fontfile=font_file, color=GRAY)
        shape.draw_line(fitz.Point(x0, 90), fitz.Point(x1, 90))
        shape.finish(color=RULE, width=0.55)
        # 꼬리말
        shape.draw_line(fitz.Point(x0, 803), fitz.Point(x1, 803))
        shape.finish(color=RULE, width=0.45)
        shape.insert_text(fitz.Point(x0, 818.5), FOOTER_TEXT, fontsize=7.5, fontname="NotoKR", fontfile=font_file, color=GRAY)
        pno = str(i + 1)
        tw = font.text_length(pno, fontsize=10)
        shape.insert_text(fitz.Point(x1 - tw, 819.5), pno, fontsize=10, fontname="NotoKR", fontfile=font_file, color=PAGE_NO)
        shape.commit()
    doc.save(out_path, garbage=3, deflate=True)
    return len(doc)


def main():
    lines = open(MD, encoding="utf-8").read().splitlines()
    chapters = parse(lines)
    tmp = tempfile.mkdtemp(prefix="report_html_")
    pass1 = os.path.join(tmp, "pass1.pdf")
    build_html(chapters, {})
    print_pdf(pass1)
    toc_pages = chapter_pages(pass1)
    pass2 = os.path.join(tmp, "pass2.pdf")
    build_html(chapters, toc_pages)
    print_pdf(pass2)
    n = stamp(pass2, PDF_OUT, chapters)
    shutil.rmtree(tmp, ignore_errors=True)
    print("HTML", HTML_OUT)
    print("PDF", PDF_OUT)
    print("PAGES", n)
    print("CHAPTER_PAGES", toc_pages)


if __name__ == "__main__":
    main()
