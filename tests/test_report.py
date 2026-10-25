import os
import tempfile
import unittest
from unittest.mock import patch

from src import build_report


class ReportTests(unittest.TestCase):
    def test_escape_code_and_render_bold(self):
        rendered = build_report.inline("`x < 3` **후보**")
        self.assertIn("<code>x &lt; 3</code>", rendered)
        self.assertIn("<b>후보</b>", rendered)

    def test_local_document_link_is_portable_in_pdf(self):
        rendered = build_report.inline("[실험 기록](../docs/03-experiment-log.md)")
        self.assertIn("https://github.com/posco-3bungi-pdm/pdm-project/blob/main/docs/03-experiment-log.md", rendered)
        self.assertNotIn("file://", rendered)

    def test_escaped_pipe_does_not_split_table_cell(self):
        cells = build_report.split_row(r"| 기준 | \|Z\| > 3 |")
        self.assertEqual(cells, ["기준", r"\|Z\| > 3"])

    def test_image_uses_markdown_directory(self):
        with tempfile.TemporaryDirectory() as root:
            folder = os.path.join(root, "reports")
            os.makedirs(os.path.join(folder, "assets"))
            with open(os.path.join(folder, "assets", "a.png"), "wb") as target:
                target.write(b"image")
            with patch.object(build_report, "MD", os.path.join(folder, "report.md")):
                rendered = build_report.render_image("그림 1-1. 표지", "assets/a.png")
            self.assertIn("reports/assets/a.png", rendered.replace("\\", "/"))
            self.assertNotIn("reports/reports", rendered)

    def test_missing_image_stops_export(self):
        with self.assertRaises(FileNotFoundError):
            build_report.render_image("없는 그림", "assets/not-present.png")

    def test_actual_report_has_all_chapters_and_images(self):
        with open(build_report.MD, encoding="utf-8") as source:
            chapters = build_report.parse(source.read().splitlines())
        self.assertEqual([c["num"] for c in chapters if c["num"]], list(range(1, 10)))
        images = []
        for chapter in chapters:
            for kind, value in chapter["blocks"]:
                if kind == "image":
                    images.append(value)
        self.assertEqual(len(images), 6)
        for caption, path in images:
            with self.subTest(path=path):
                self.assertIn("<figure>", build_report.render_image(caption, path))


if __name__ == "__main__":
    unittest.main()
