"""Coverage and failure-boundary tests for the complete accuracy overview."""

import json
import os
from pathlib import Path
import tempfile
import unittest

from benchmarks.accuracy.overview import ROOT, SUITES, case_page, compose, load_suites, rebase_links, verify


class OverviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.dest = self.repo / ROOT
        self.dest.mkdir(parents=True)
        self.original = "# Accuracy against a real Zebra printer\n"
        for cid in ["ink", "blank"]:
            self.original += f"[{cid}](comparisons/cases/{cid}.md)\n"
        for key, _, gallery in SUITES:
            rows = [
                dict(case="ink", library="a", score=1.0, iou=1.0, status="rendered"),
                dict(case="ink", library="b", score=0.0, status="timeout"),
                dict(case="blank", library="a", score=None, iou=1.0, status="blank"),
                dict(case="blank", library="b", score=None, iou=1.0, status="blank"),
            ]
            data = dict(cases=[dict(name=c, group=c) for c in ["ink", "blank"]], results=rows, measured_utc="saved",
                        relations=[dict(set="equivalence", library="a", cases=["ink", "blank"], status="inconclusive")])
            path = self.dest.parent / key / "results.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
            if key != "accuracy":
                path = self.dest / gallery / "results.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(dict(results=rows)))
            for cid in ["ink", "blank"]:
                page = self.repo / case_page(key, cid)
                page.parent.mkdir(parents=True, exist_ok=True)
                text = ""
                for row in [r for r in rows if r["case"] == cid]:
                    text += "## " + row["library"] + "\n"
                    if row["status"] == "timeout":
                        continue
                    prefix = cid + "-" + row["library"]
                    assets = ROOT if key == "accuracy" else ROOT + "/" + gallery
                    for filename in [f"docs/benchmarks/{key}/images/{prefix}.png", assets + f"/images/{prefix}-diff.png"]:
                        image = self.repo / filename
                        image.parent.mkdir(parents=True, exist_ok=True)
                        image.write_bytes(b"fixture")
                        text += f"[image]({os.path.relpath(image, page.parent)})\n"
                page.write_text(text)

    def test_all_suites_categories_failures_and_blank_differences_are_visible(self):
        suites = load_suites(self.dest)
        text = compose(self.original, suites)
        verify(self.dest, suites, text)
        self.assertEqual(compose(text, suites), text)
        for suite in suites:
            for case in suite["cases"]:
                self.assertIn(os.path.relpath(case_page(suite["key"], case["name"]), ROOT), text)
            self.assertIn(f"| {suite['title']} | ink | 1 | 100.00% (1) | 0.00% (1) |", text)
        self.assertIn("0.00% · timeout", text)
        self.assertIn("unscored · blank", text)
        self.assertIn("| 2 | 2 | 4 | 2 | 3 | saved |", text)
        self.assertIn("inconclusive", text)
        self.assertNotIn("](comparisons/README.md)", text)
        self.assertIn("](#argument-and-archived-barcode-details)", text)
        for suite in suites:
            for lib in suite["libraries"]:
                self.assertIn(f"]({suite['gallery']}/libraries/{lib}.md)", text)

    def test_retired_index_and_inbound_links_fail_publication(self):
        suites = load_suites(self.dest)
        text = compose(self.original, suites)
        obsolete = self.dest / "comparisons/README.md"
        obsolete.write_text("old index")
        with self.assertRaisesRegex(ValueError, "Obsolete comparison index"):
            verify(self.dest, suites, text)
        obsolete.unlink()
        (self.dest / "comparisons/libraries").mkdir()
        (self.dest / "comparisons/libraries/a.md").write_text("[Old index](../README.md)")
        with self.assertRaisesRegex(ValueError, "Link to obsolete comparison index"):
            verify(self.dest, suites, text)

    def test_missing_suite_or_comparison_cannot_silently_disappear(self):
        path = self.dest / "comparisons/features/results.json"
        data = json.loads(path.read_text())
        data["results"].pop()
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Incomplete.*conformance"):
            load_suites(self.dest)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            load_suites(self.dest)

    def test_missing_case_image_or_library_fails_publication_check(self):
        suites = load_suites(self.dest)
        text = compose(self.original, suites)
        page = self.repo / case_page("layout-accuracy", "ink")
        original = page.read_text()
        page.write_text(original.replace("## b\n", ""))
        with self.assertRaisesRegex(ValueError, "omits renderer"):
            verify(self.dest, suites, text)
        page.write_text(original)
        (self.dest / "comparisons/layout/images/ink-a-diff.png").unlink()
        with self.assertRaisesRegex(ValueError, "broken link|missing comparison image"):
            verify(self.dest, suites, text)
        page.unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.dest, suites, text)

    def test_case_names_cannot_collide_between_corpora(self):
        self.assertEqual(len({case_page(key, "same") for key, _, _ in SUITES}), len(SUITES))
        self.assertEqual(case_page("accuracy", "argument-code39-ratio-2"), ROOT + "/comparisons/cases/argument-code39-ratio-2.md")

    def test_alias_rebases_local_links_but_preserves_external_and_anchor_links(self):
        text = "[diff](../images/x.png) [library](../libraries/a.md#a) [web](https://example.org/x) [anchor](#a)"
        moved = rebase_links(text, ROOT + "/comparisons/features/cases/x.md", case_page("conformance", "x"))
        self.assertIn("](../features/images/x.png)", moved)
        self.assertIn("](../features/libraries/a.md#a)", moved)
        self.assertIn("](https://example.org/x)", moved)
        self.assertIn("](#a)", moved)


if __name__ == "__main__":
    unittest.main()
