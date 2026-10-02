"""Exercise device selection through the real compiled comparison adapter."""
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from benchmarks.accuracy.pixels import sha
from build.render import render


class CanvasProfileTest(unittest.TestCase):
    def test_device_canvas_contract(self):
        # ZQ610 V100.21.21Z observations and profile contract:
        # references/zq610-plus-v1/{canvas-height-120,width-boundary-65,
        # canvas-width-832,width-late-grow,width-late-shrink}/zq610.zpl
        cases = [
            ("^PW384^LL120^FO20,20^GB30,20,3^FS", (384, 120), (384, 2030)),
            ("^PW65^LL200^FO0,0^GB10,10,2^FS", (65, 200), (128, 2030)),
            ("^PW832^LL200^FO0,0^GB10,10,2^FS", (832, 200), (384, 2030)),
            ("^PW120^LL200^FO0,0^GB10,10,2^FS^PW384", (384, 200), (128, 2030)),
            ("^PW384^LL200^FO0,0^GB10,10,2^FS^PW120", (120, 200), (384, 2030)),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.zpl"
            previews = [(384, 120), (128, 200), (832, 200), (128, 200), (384, 200)]
            for index, (body, default, mobile) in enumerate(cases):
                source.write_text("^XA" + body + "^XZ")
                for profile, size in [("zd621-203dpi", default), ("zq610-plus-203dpi", mobile), ("zd621-preview-203dpi", previews[index])]:
                    with self.subTest(index=index, profile=profile):
                        images = root / f"{index}-{profile}"
                        metadata = root / "row.json"
                        render(dict(source=str(source), sha256=sha(source),
                                    width=384, height=2030, render_profile=profile,
                                    library="library_codyps-zpl", row={}), metadata, images)
                        self.assertEqual(json.loads(metadata.read_text())["status"], "rendered")
                        with Image.open(images / "image.png") as image:
                            self.assertEqual(image.size, size)


if __name__ == "__main__":
    unittest.main()
