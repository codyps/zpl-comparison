"""Exercise the real SDK, including binary input and virtual-printer isolation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from build import renderer_session as sessions
from build.native_build import source_size


class NeodynamicAdapterTest(unittest.TestCase):
    def setUp(self):
        self.deployment = Path('library_neodynamic').resolve()
        self.command = [str(self.deployment / value) if (self.deployment / value).exists() else value
                        for value in json.loads((self.deployment / 'command.json').read_text())]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {**os.environ, 'DOTNET_ROOT': str(self.deployment / 'runtime'),
                    'DOTNET_CLI_HOME': str(self.root), 'HOME': str(self.root), 'TMPDIR': str(self.root),
                    'LD_LIBRARY_PATH': str(self.deployment) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', ''),
                    'ZPL_FONT_DIR': '', 'ZPL_RENDER_PROFILE': 'zd621-203dpi', 'ZPL_BENCH_MEMORY': '1'}

    def invoke(self, source, mode='accuracy', width=192, height=120):
        path, image = self.root / 'input.zpl', self.root / 'output.png'
        path.write_bytes(source)
        image.unlink(missing_ok=True)
        args = [mode, str(path), '2', str(image), str(width), str(height)]
        result = subprocess.run(self.command + args, cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=30)
        return result, args, image

    @staticmethod
    def raster(path):
        with Image.open(path) as image:
            return image.convert('RGB')

    def assert_document_equal(self, expected, actual):
        self.assertEqual(actual.size, expected.size)
        # Trial stamps can overlay the document, changing even its black pixels.
        # Exclude colored/gray stamp pixels in either image, including their
        # antialiased boundary. These tests use binary graphics and black boxes.
        masks = []
        for image in (expected, actual):
            mask = Image.new('L', image.size)
            mask.putdata([0 if pixel in {(0, 0, 0), (255, 255, 255)} else 255
                          for pixel in image.get_flattened_data()])
            masks.append(mask)
        mask = ImageChops.lighter(*masks).filter(ImageFilter.MaxFilter(3))
        self.assertLess(sum(bool(value) for value in mask.get_flattened_data()),
                        expected.width * expected.height * 3 // 4)
        difference = ImageChops.difference(expected, actual)
        difference.paste((0, 0, 0), mask=mask)
        self.assertIsNone(difference.getbbox(), 'Document pixels changed outside the trial stamp')
        return mask

    def test_trial_mask_still_detects_leaked_graphics(self):
        expected = Image.new('RGB', (192, 120), 'white')
        ImageDraw.Draw(expected).rectangle((10, 50, 69, 79), outline='black', width=4)
        stamped = expected.copy()
        ImageDraw.Draw(stamped).line((14, 50, 30, 66), fill=(12, 44, 27), width=2)
        self.assert_document_equal(expected, stamped)
        leaked = stamped.copy()
        ImageDraw.Draw(leaked).rectangle((100, 75, 163, 106), fill='black')
        with self.assertRaisesRegex(AssertionError, 'Document pixels changed'):
            self.assert_document_equal(expected, leaked)

    def test_canvas_and_png_timing_protocol(self):
        source = b'^XA^FO10,50^GB20,20,2^FS^XZ'
        result, _, image = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(image) as png:
            self.assertEqual(png.size, (192, 120))
        result, _, image = self.invoke(source, mode='png')
        self.assertEqual(result.returncode, 0, result.stderr)
        timing = json.loads(result.stdout)
        self.assertEqual(timing['iterations'], 2)
        self.assertGreater(timing['ns'], 0)
        self.assertGreater(timing['checksum'], 0)
        result, _, _ = self.invoke(source, mode='parse')
        self.assertNotEqual(result.returncode, 0)

    def test_binary_graphics_match_ascii_hex_without_text_decoding(self):
        # A large frame keeps substantial document ink outside the trial stamp.
        data = b'\xff' * 8 + (b'\x80' + b'\0' * 6 + b'\x01') * 30 + b'\xff' * 8
        prefix, suffix = b'^XA^FO10,60', b'^FS^XZ'
        result, _, image = self.invoke(prefix + b'^GFB,256,256,8,' + data + suffix)
        self.assertEqual(result.returncode, 0, result.stderr)
        binary = self.raster(image)
        result, _, image = self.invoke(prefix + b'^GFA,256,256,8,' + data.hex().upper().encode() + suffix)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_document_equal(binary, self.raster(image))
        ideal = Image.new('RGB', binary.size, 'white')
        ImageDraw.Draw(ideal).rectangle((10, 60, 73, 91), outline='black')
        mask = self.assert_document_equal(ideal, binary)
        visible_ink = sum(pixel == (0, 0, 0) and not excluded
                          for pixel, excluded in zip(ideal.get_flattened_data(), mask.get_flattened_data()))
        self.assertGreater(visible_ink, (64 * 2 + 30 * 2) // 2)

    def test_probe_empty_and_multiple_label_contracts(self):
        result, _, image = self.invoke(b'', mode='probe-render')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'accepted-empty')
        self.assertFalse(image.exists())
        result, _, _ = self.invoke(b'^XA^FO10,10^GB20,20,2^FS^XZ', mode='probe-render')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'accepted')
        result, _, image = self.invoke(b'^XA^XZ^XA^XZ')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(image.exists())

    def test_session_does_not_retain_downloads_or_printer_state(self):
        self.addCleanup(sessions.close_all)
        cases = [b'^XA^FO10,50^GB60,30,4^FS^XZ',
                 b'~DGR:LEAK.GRF,256,8,' + b'FF' * 256 + b'^XA^LH30,20^POI^FO0,0^XGR:LEAK.GRF,1,1^FS^XZ',
                 b'^XA^FO10,60^XGR:LEAK.GRF,1,1^FS^XZ',
                 b'^XA^FO10,50^GB30,20,3^FS^XZ']
        for source in cases:
            fresh, args, image = self.invoke(source)
            expected = self.raster(image) if fresh.returncode == 0 else None
            image.unlink(missing_ok=True)
            reused = sessions.run(self.command, args, cwd=str(self.root), env=self.env,
                                  timeout=30, identity='neodynamic')
            self.assertEqual(reused.returncode, fresh.returncode, reused.stderr)
            if expected is not None:
                self.assert_document_equal(expected, self.raster(image))
        self.assertTrue(any(session.count > 1 for session in sessions._sessions.values()))

    def test_proprietary_source_is_unavailable(self):
        size = source_size(self.root, 'neodynamic')
        self.assertIn('unavailable', size['source_status'])
        self.assertNotIn('bytes', size)


if __name__ == '__main__':
    unittest.main()
