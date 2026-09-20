"""Navigation thumbnails must retain outlying ink and leave scored pixels intact."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from accuracy.presentation import viewport, preview, MAX_SIZE


class PresentationTests(unittest.TestCase):
    def test_shared_frame_keeps_outlying_renderer_ink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for name, y in [("printer", 10), ("library", 280)]:
                image = Image.new("RGB", (640, 500), "white")
                image.putpixel((10, y), (0, 0, 0))
                path = root / (name + ".png")
                image.save(path)
                paths.append(path)
            before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            frame = viewport(paths)
            self.assertEqual(frame, (640, 293))
            target = root / "thumbnail.png"
            link = preview(paths[0], target, frame, root / "case.md", "Printer")
            self.assertIn("](printer.png)", link)
            with Image.open(target) as image:
                self.assertLessEqual(image.width, MAX_SIZE[0])
                self.assertLessEqual(image.height, MAX_SIZE[1])
            preview(paths[0], target, frame, root / "case.md", "Printer", check=True)
            self.assertEqual(
                before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            )
            Image.new("RGB", (1, 1), "red").save(target)
            with self.assertRaisesRegex(ValueError, "Stale compact preview"):
                preview(
                    paths[0], target, frame, root / "case.md", "Printer", check=True
                )
