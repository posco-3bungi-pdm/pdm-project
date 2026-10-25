"""문서의 로컬 링크와 저장된 모델 지표를 확인한다. 모델은 실행하지 않는다."""

import argparse
import csv
import glob
import math
import os
import re
from urllib.parse import unquote, urlsplit


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITHUB_ROOT = "https://github.com/posco-3bungi-pdm/pdm-project/"


def without_code(text):
    """코드 예시에 적힌 경로와 기호는 검사하지 않는다."""
    lines = []
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            lines.append("")
        elif fence is not None:
            lines.append("")
        else:
            lines.append(re.sub(r"`+[^`]*`+", "", line))
    return "\n".join(lines)


def markdown_targets(text):
    """괄호가 들어간 파일명과 HTML 이미지 경로도 읽는다."""
    text = without_code(text)
    for match in re.finditer(r"!?\[[^\]\n]*\]\(", text):
        start = match.end()
        depth = 1
        end = start
        while end < len(text) and depth:
            char = text[end]
            if char == "\\":
                end += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            end += 1
        if depth:
            continue
        value = text[start:end - 1].strip()
        if value.startswith("<"):
            value = value[1:value.find(">")]
        else:
            value = re.split(r'\s+["\']', value, maxsplit=1)[0]
        yield text.count("\n", 0, match.start()) + 1, value

    for match in re.finditer(r'(?:src|href|srcset)=["\']([^"\']+)["\']', text):
        value = match.group(1)
        if "srcset" in match.group(0):
            value = value.split(",")[0].split()[0]
        yield text.count("\n", 0, match.start()) + 1, value


def check_links(root, path):
    with open(path, encoding="utf-8-sig") as source:
        text = source.read()
    errors = []
    root = os.path.realpath(root)
    for line, value in markdown_targets(text):
        if value.startswith(GITHUB_ROOT):
            tail = value[len(GITHUB_ROOT):]
            if not tail.startswith(("blob/main/", "raw/main/", "tree/main/")):
                continue
            value = "/" + tail.split("/", 2)[2]
        url = urlsplit(value)
        if url.scheme or url.netloc or not url.path:
            continue
        relative = unquote(url.path)
        if relative.startswith("/"):
            target = os.path.join(root, relative.lstrip("/"))
        else:
            target = os.path.join(os.path.dirname(path), relative)
        target = os.path.realpath(target)
        if os.path.commonpath([root, target]) != root:
            errors.append(f"{path}:{line}: 저장소 밖 경로: {value}")
        elif not os.path.exists(target):
            errors.append(f"{path}:{line}: 없는 경로: {value}")
    return errors


def check_report_text(path):
    with open(path, encoding="utf-8-sig") as source:
        text = without_code(source.read())
    errors = []
    for number, line in enumerate(text.splitlines(), 1):
        if "·" in line:
            errors.append(f"{path}:{number}: 가운데점")
        if line.count("~") >= 2:
            errors.append(f"{path}:{number}: 취소선으로 보일 수 있는 물결표")
        if re.search(r"\{w=\d+\}", line):
            errors.append(f"{path}:{number}: GitHub에서 지원하지 않는 그림 폭 표기")
    return errors


def check_metric_row(row):
    """혼동행렬의 합과 소수 넷째 자리로 저장한 지표를 대조한다."""
    errors = []
    counts = {}
    for key in ("TP", "FP", "FN", "TN"):
        try:
            value = float(row[key])
            if not math.isfinite(value) or value < 0 or not value.is_integer():
                raise ValueError
            counts[key] = int(value)
        except (KeyError, TypeError, ValueError):
            errors.append(f"{key}: 0 이상의 정수가 아님")
    if errors:
        return errors

    tp, fp, fn, tn = [counts[key] for key in ("TP", "FP", "FN", "TN")]
    expected = {
        "시험 행": tp + fp + fn + tn,
        "LABEL 1": tp + fn,
        "Precision": tp / (tp + fp) if tp + fp else None,
        "Recall": tp / (tp + fn) if tp + fn else None,
        "F1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }
    for key, target in expected.items():
        if key not in row:
            continue
        saved = row[key]
        if target is None:
            # 분모가 0인 경우 기존 파일의 0, 빈칸, NaN을 모두 허용한다.
            if str(saved).strip().lower() not in ("", "nan", "none", "0", "0.0", "0.0000"):
                errors.append(f"{key}: 분모가 0인데 값이 있음")
            continue
        try:
            value = float(saved)
        except (TypeError, ValueError):
            value = float("nan")
        tolerance = 0 if key in ("시험 행", "LABEL 1") else 0.00005001
        if not math.isfinite(value) or abs(value - target) > tolerance:
            errors.append(f"{key}: 저장값 {saved}, 계산값 {target}")
    return errors


def check_summary(path):
    errors = []
    with open(path, encoding="utf-8-sig", newline="") as source:
        rows = csv.DictReader(source)
        required = {"TP", "FP", "FN", "TN"}
        if not required.issubset(rows.fieldnames or []):
            return [f"{path}: 혼동행렬 컬럼이 없음"]
        count = 0
        for number, row in enumerate(rows, 2):
            count += 1
            for message in check_metric_row(row):
                errors.append(f"{path}:{number}: {message}")
        if count == 0:
            errors.append(f"{path}: 결과 행이 없음")
    return errors


def document_files(root):
    names = ["README.md", "CONTRIBUTING.md", "notebooks/README.md"]
    for folder in ("docs", "reports", "src", "tests"):
        names += glob.glob(os.path.join(folder, "*.md"), root_dir=root)
    return [os.path.join(root, name) for name in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", help="v7 최종 입력의 summary CSV 폴더. 원본은 수정하지 않음")
    args = parser.parse_args()
    errors = []
    documents = document_files(ROOT)
    for path in documents:
        errors += check_links(ROOT, path)
    for name in ("reports/결과보고서.md", "docs/03-experiment-log.md"):
        errors += check_report_text(os.path.join(ROOT, name))

    summaries = []
    if args.results_dir:
        for zone in ["CLN"] + ["Z" + str(i) for i in range(1, 9)]:
            name = "cal01_base_v7_" + zone + "_common_roll10_zpast_opcommon_furnace_control_summary.csv"
            path = os.path.join(args.results_dir, name)
            if not os.path.isfile(path):
                errors.append("결과 파일 없음: " + path)
                continue
            summaries.append(path)
            errors += check_summary(path)

    for message in errors:
        print(message)
    if errors:
        return 1
    print(f"PASS: 문서 {len(documents)}개, 모델 지표 파일 {len(summaries)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
