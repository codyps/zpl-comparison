"""Compatibility pages must agree, retain evidence boundaries and resolve links."""

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import compatibility as catalog


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = catalog.artifacts()
        cls.support = catalog.load(catalog.SUPPORT)

    def test_every_library_command_and_feature_has_a_page(self):
        self.assertEqual(
            len(
                [
                    n
                    for n in self.generated
                    if n.startswith("libraries/") and not n.endswith("README.md")
                ]
            ),
            12,
        )
        self.assertEqual(
            len(
                [
                    n
                    for n in self.generated
                    if n.startswith("commands/") and not n.endswith("README.md")
                ]
            ),
            224,
        )
        groups = {c["group"] for c in catalog.load(catalog.CORPUS)["cases"]}
        self.assertEqual(
            {f"features/{g}.md" for g in groups},
            {
                n
                for n in self.generated
                if n.startswith("features/") and not n.endswith("README.md")
            },
        )
        for name, data in self.generated.items():
            self.assertEqual((catalog.DEST / name).read_bytes(), data, name)

    def test_prefix_and_named_font_pages_do_not_collide(self):
        commands = ["^CC", "~CC", "^A", "^A@"]
        slugs = [catalog.command_slug(c) for c in commands]
        self.assertEqual(len(set(slugs)), 4)
        self.assertTrue(all("commands/" + s + ".md" in self.generated for s in slugs))

    def test_codyps_inventory_retains_late_graphics_handlers(self):
        # These handlers moved beyond the inventory's former fixed line range.
        for command in ["^GB", "^GE", "^GC", "~DG", "^GF", "^XG", "^FS"]:
            with self.subTest(command=command):
                self.assertEqual(catalog.state(self.support, "codyps-zpl", command), "D")

    def test_both_directions_show_same_evidence(self):
        for library in catalog.LIBRARIES:
            library_text = self.generated[f"libraries/{library}.md"].decode()
            for command in ["^B3", "^BQ", "^A@", "~DG", "^MD"]:
                command_text = self.generated[
                    "commands/" + catalog.command_slug(command) + ".md"
                ].decode()
                expected = catalog.LABELS[catalog.state(self.support, library, command)]
                library_row = next(
                    line
                    for line in library_text.splitlines()
                    if line.startswith(f"| [`{command}`]")
                )
                command_row = next(
                    line
                    for line in command_text.splitlines()
                    if line.startswith(f"| [{catalog.LIBRARIES[library][0]}]")
                )
                self.assertIn(expected, library_row)
                self.assertIn(expected, command_row)
        self.assertEqual(catalog.state(self.support, "go", "^B3"), "I")

    def test_measurement_is_not_support_and_absence_is_not_failure(self):
        self.assertIn("N/A", catalog.accuracy_summary("builder", []))
        self.assertEqual(catalog.accuracy_summary("codyps-zpl", []), "Not measured")
        rows = [
            dict(library="codyps-zpl", score=0, status="error"),
            dict(library="codyps-zpl", score=1, status="rendered", exact=True),
        ]
        result = catalog.accuracy_summary("codyps-zpl", rows)
        self.assertIn("1/2 exact", result)
        self.assertIn("50.0%", result)
        self.assertIn(
            "Negative-input observations",
            catalog.execution_summary(
                "codyps-zpl", [dict(library="codyps-zpl", validity="invalid", status="error")]
            ),
        )

    def test_stale_execution_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            path.write_text(json.dumps(dict(manifest_sha256="stale", results=[])))
            with patch.object(catalog, "CONFORMANCE", path):
                with self.assertRaisesRegex(ValueError, "Stale conformance results"):
                    catalog.artifacts()

    def test_incidental_commands_do_not_receive_printer_scores(self):
        # Every reference label has XA, but none is a focused XA fidelity case.
        page = self.generated["commands/format-xa.md"].decode()
        self.assertIn("No focused printer measurements yet.", page)
        self.assertNotIn("% IoU", page)

    def test_all_relative_links_resolve(self):
        for name, data in self.generated.items():
            if not name.endswith(".md"):
                continue
            page = catalog.DEST / name
            for url in re.findall(r"\]\(([^)]+)\)", data.decode()):
                if "://" in url or url.startswith("#"):
                    continue
                target = (page.parent / url.split("#")[0]).resolve()
                self.assertTrue(target.exists(), f"{name}: {url}")


if __name__ == "__main__":
    unittest.main()
