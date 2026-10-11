"""Native deployments must render after relocation without loader overrides."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image


class NativeAdapterTest(unittest.TestCase):
    def test_forge_initialization_and_reused_fonts(self):
        deployment = Path("library_forge").resolve()
        command = [str(deployment / item) for item in json.loads((deployment / "command.json").read_text())]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "image.png"
            result = subprocess.run(command + ["init", str(root / "missing.zpl"), "1", str(output)],
                                    cwd=root, capture_output=True, text=True, check=True, timeout=30)
            timing = json.loads(result.stdout)
            self.assertEqual(timing["iterations"], 1)
            self.assertGreater(timing["ns"], 0)
            self.assertFalse(output.exists())
            source = root / "input.zpl"
            source.write_text("^XA^FO10,10^A0N,30,20^FDShared fonts^FS^XZ")
            subprocess.run(command + ["accuracy", str(source), "1", str(output)],
                           cwd=root, capture_output=True, check=True, timeout=30)
            expected = output.read_bytes()
            result = subprocess.run(command + ["png", str(source), "3", str(output)],
                                    env={**os.environ, "ZPL_BENCH_MEMORY": "1"}, cwd=root,
                                    capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(json.loads(result.stdout)["iterations"], 3)
            self.assertEqual(output.read_bytes(), expected)

    def test_relocated_renderers(self):
        for library in ("codyps-zpl", "labelize", "forge", "go", "ffi", "zebrash"):
            with self.subTest(library=library), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                deployment = root / "deployment"
                shutil.copytree(Path("library_" + library).resolve(), deployment)
                source = root / "input.zpl"
                source.write_text("^XA^PW320^LL100^FO10,10^GB100,40,3^FS^XZ")
                output = root / "image.png"
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith(("LD_", "DYLD_", "LIBZPL_", "ZPL_"))}
                command = [str(deployment / item) for item in json.loads((deployment / "command.json").read_text())]
                subprocess.run(command + ["accuracy", str(source), "1", str(output), "320", "100"],
                               cwd=root, env=env, check=True, capture_output=True, timeout=30)
                with Image.open(output) as image:
                    self.assertEqual(image.size, (320, 100))
                    self.assertLess(image.convert("L").getextrema()[0], 128)


if __name__ == "__main__":
    unittest.main()
