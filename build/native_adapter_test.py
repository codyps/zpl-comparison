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
