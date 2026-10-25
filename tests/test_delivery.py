import os
import tempfile
import unittest

from src.check_delivery import (
    ROOT,
    check_links,
    check_metric_row,
    check_report_text,
    check_summary,
    document_files,
    markdown_targets,
)


class LinkTests(unittest.TestCase):
    def test_links_in_repository(self):
        errors = []
        for path in document_files(ROOT):
            errors += check_links(ROOT, path)
        self.assertEqual(errors, [])

    def test_reports_have_no_strikethrough_or_private_width_syntax(self):
        for name in ("reports/결과보고서.md", "docs/03-experiment-log.md"):
            with self.subTest(name=name):
                self.assertEqual(check_report_text(os.path.join(ROOT, name)), [])

    def test_parentheses_and_angle_brackets_in_filename(self):
        text = "[PDF](<보고서(3조).pdf>)\n![그림](../figures/검토(1).png)"
        self.assertEqual(list(markdown_targets(text)), [(1, "보고서(3조).pdf"), (2, "../figures/검토(1).png")])

    def test_code_examples_are_not_links(self):
        text = "```md\n![예시](없는.png)\n```\n`[예시](없는.md)`\n[실제](README.md)"
        self.assertEqual(list(markdown_targets(text)), [(5, "README.md")])

    def test_github_image_relative_path_regression(self):
        with tempfile.TemporaryDirectory() as root:
            folder = os.path.join(root, "reports")
            os.makedirs(os.path.join(folder, "assets"))
            with open(os.path.join(folder, "assets", "cover.png"), "wb") as target:
                target.write(b"image")
            path = os.path.join(folder, "report.md")
            with open(path, "w", encoding="utf-8") as target:
                target.write("![표지](reports/assets/cover.png)")
            self.assertEqual(len(check_links(root, path)), 1)
            with open(path, "w", encoding="utf-8") as target:
                target.write("![표지](assets/cover.png)")
            self.assertEqual(check_links(root, path), [])

    def test_url_encoded_filename(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "보고서 (1).pdf"), "wb") as target:
                target.write(b"pdf")
            path = os.path.join(root, "README.md")
            with open(path, "w", encoding="utf-8") as target:
                target.write("[PDF](%EB%B3%B4%EA%B3%A0%EC%84%9C%20%281%29.pdf)")
            self.assertEqual(check_links(root, path), [])

    def test_external_links_do_not_require_network(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "README.md")
            with open(path, "w", encoding="utf-8") as target:
                target.write('[참고](https://example.com/a)\n<img src="https://example.com/a.png">')
            self.assertEqual(check_links(root, path), [])

    def test_strikethrough_range_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "report.md")
            with open(path, "w", encoding="utf-8") as target:
                target.write("Z3~Z6 출력, Z1~Z8 동시 변화")
            self.assertEqual(len(check_report_text(path)), 1)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.row = {"TP": "96", "FP": "67", "FN": "69", "TN": "3401",
                    "시험 행": "3633", "LABEL 1": "165", "Precision": "0.5890", "Recall": "0.5818", "F1": "0.5854"}

    def test_rounded_metrics_match_counts(self):
        self.assertEqual(check_metric_row(self.row), [])

    def test_wrong_f1_is_reported(self):
        self.row["F1"] = "0.875"
        self.assertTrue(any("F1" in error for error in check_metric_row(self.row)))

    def test_swapped_precision_and_recall_are_reported(self):
        self.row["Precision"], self.row["Recall"] = self.row["Recall"], self.row["Precision"]
        self.assertEqual(len(check_metric_row(self.row)), 2)

    def test_wrong_total_is_reported(self):
        self.row["시험 행"] = "4000"
        self.assertTrue(any("시험 행" in error for error in check_metric_row(self.row)))

    def test_wrong_positive_count_is_reported(self):
        self.row["LABEL 1"] = "100"
        self.assertTrue(any("LABEL 1" in error for error in check_metric_row(self.row)))

    def test_missing_or_negative_counts_fail(self):
        for value in ("-1", "0.5", "nan", "inf", ""):
            with self.subTest(value=value):
                self.row["TP"] = value
                self.assertTrue(check_metric_row(self.row))

    def test_all_zero_dummy_has_undefined_precision(self):
        row = {"TP": "0", "FP": "0", "FN": "165", "TN": "3468",
               "Precision": "", "Recall": "0", "F1": "0"}
        self.assertEqual(check_metric_row(row), [])

    def test_no_positive_labels_but_false_alarms(self):
        row = {"TP": "0", "FP": "5", "FN": "0", "TN": "95",
               "Precision": "0", "Recall": "nan", "F1": "0"}
        self.assertEqual(check_metric_row(row), [])

    def test_empty_evaluation_is_not_a_high_score(self):
        row = {"TP": "0", "FP": "0", "FN": "0", "TN": "0", "F1": "0.9"}
        self.assertTrue(check_metric_row(row))

    def test_summary_csv_with_bom(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "summary.csv")
            with open(path, "w", encoding="utf-8-sig", newline="") as target:
                target.write("TP,FP,FN,TN,F1\n1,0,1,8,0.6667\n")
            self.assertEqual(check_summary(path), [])

    def test_empty_or_wrong_summary_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "summary.csv")
            for text in ("", "TP,FP,FN,TN\n", "model,F1\nRF,0.9\n"):
                with self.subTest(text=text):
                    with open(path, "w", encoding="utf-8") as target:
                        target.write(text)
                    self.assertTrue(check_summary(path))


if __name__ == "__main__":
    unittest.main()
