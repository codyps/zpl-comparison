"""Exercise the public zplkit APIs through the deployed comparison protocol."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image


class ZplkitAdapterTest(unittest.TestCase):
    def setUp(self):
        deployment = Path('library_zplkit-ts').resolve()
        self.command = [str(deployment / arg) if (deployment / arg).exists() else arg
                        for arg in json.loads((deployment / 'command.json').read_text())]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'output.png'

    def invoke(self, mode, source, profile='zd621-203dpi'):
        path = self.root / 'input.zpl'
        path.write_bytes(source)
        self.output.unlink(missing_ok=True)
        return subprocess.run(self.command + [mode, str(path), '2', str(self.output), '192', '120'],
                              cwd=self.root, env={**os.environ, 'ZPL_RENDER_PROFILE': profile,
                                                'ZPL_BENCH_MEMORY': '1'},
                              capture_output=True, text=True, timeout=30, check=True)

    def test_native_canvas_geometry_and_profiles(self):
        for profile in ['zd621-203dpi', 'zq610-plus-203dpi', 'gx430t-300dpi']:
            self.invoke('accuracy', b'^XA^FO10,20^GB30,20,3^FS^XZ', profile)
            with Image.open(self.output) as image:
                self.assertEqual(image.size, (192, 120))
                self.assertEqual(image.convert('L').getpixel((10, 20)), 0)
                self.assertEqual(image.convert('L').getpixel((15, 25)), 255)

    def test_utf8_rejection_and_public_parser_warnings(self):
        for mode in ['probe-parse', 'probe-render']:
            result = self.invoke(mode, b'^XA^FD\xff^FS^XZ')
            self.assertEqual(result.stdout.strip(), 'rejected')
            self.assertFalse(self.output.exists())
        self.invoke('parse', b'^XA^PWbogus^XZ')
        self.assertTrue(json.loads(self.output.read_text())['diagnostics'])
        self.assertEqual(self.invoke('probe-parse', b'^XA^PWbogus^XZ').stdout.strip(), 'accepted')

    def test_render_requires_one_label_and_timing_repeats_work(self):
        source = b'^XA^FO10,20^GB30,20,3^FS^XZ'
        for data, verdict in [(b'', 'accepted-empty'), (source * 2, 'rejected')]:
            self.assertEqual(self.invoke('probe-render', data).stdout.strip(), verdict)
            self.assertFalse(self.output.exists())
        for mode in ['parse', 'png']:
            result = json.loads(self.invoke(mode, source).stdout)
            self.assertEqual(result['iterations'], 2)
            self.assertGreater(result['ns'], 0)
            self.assertGreater(result['checksum'], 0)


if __name__ == '__main__':
    unittest.main()
