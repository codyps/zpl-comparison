"""Verify recovered geometry, font isolation, and actual public adapter injection."""
import json
import re
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont
from benchmarks.fonts.build import unpack, build
from benchmarks.accuracy.pixels import sha
from build.font_profile import configure
from build.render import render


class FontProfileTest(unittest.TestCase):
    def test_outline_conversion_preserves_vertical_metrics(self):
        for original, converted in [('heros-cn-bold.otf', '0.ttf'), ('heros-regular.otf', 'Swiss.ttf')]:
            source = TTFont(Path('benchmarks/fonts/source') / original)
            font = TTFont(Path('comparison_fonts') / converted)
            for field in ('sCapHeight', 'sxHeight'):
                self.assertGreater(getattr(font['OS/2'], field), 0)
                self.assertEqual(getattr(font['OS/2'], field), getattr(source['OS/2'], field))

    def test_supplied_outline_text_has_visible_ink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for library in ('zplr', 'codyps-zpl'):
                for height in (16, 32, 64):
                    for font in ('^A0N', '^A@N'):
                        source = root / 'input.zpl'
                        named = ',R:TT0003M_.TTF' if font == '^A@N' else ''
                        source.write_text(f'^XA^PW400^LL100^FO10,10{font},{height},{height}{named}^FDHello 123^FS^XZ')
                        key = f'{library}-{height}-{font[2]}'
                        render(dict(source=str(source), sha256=sha(source), width=400, height=100,
                                    library='library_' + library, row=dict(library=library), font_bundle='comparison_fonts'),
                               root / (key + '.json'), root / key)
                        row = json.loads((root / (key + '.json')).read_text())
                        self.assertEqual(row['status'], 'rendered', row)
                        self.assertGreater(row['ink'], height * 3, row)

    def test_recovered_outlines_preserve_pixels_and_advances(self):
        bundle = Path('comparison_fonts')
        manifest = json.loads((bundle / 'manifest.json').read_text())
        for fid, paths in manifest['sources']['strikes'].items():
            height, glyphs = unpack(Path('benchmarks/fonts') / paths[0])
            for path in paths[1:]:
                glyphs.update(unpack(Path('benchmarks/fonts') / path)[1])
            font = TTFont(bundle / manifest['fonts'][fid])
            self.assertEqual(font['head'].unitsPerEm, height * 16)
            for cp, (advance, left, top, width, height, bits) in glyphs.items():
                key = font.getBestCmap()[cp]
                self.assertEqual(font['hmtx'][key], (advance*16, left*16))
                glyph = font['glyf'][key]
                coords, ends, _ = glyph.getCoordinates(font['glyf'])
                actual = set()
                start = 0
                for end in ends:
                    points = coords[start:end+1]
                    self.assertEqual(len(points), 4)
                    xs, ys = zip(*points)
                    for y in range(-max(ys)//16, -min(ys)//16):
                        for x in range(min(xs)//16, max(xs)//16):
                            actual.add((x, y))
                    start = end + 1
                expected = {(left+x, top+y) for y in range(height) for x in range(width)
                            if bits[(y*width+x)//8] & (128 >> ((y*width+x)%8))}
                self.assertEqual(actual, expected, (fid, cp))

    def test_native_bitmap_downloads_preserve_metrics_and_bits(self):
        bundle = Path('comparison_fonts')
        manifest = json.loads((bundle / 'manifest.json').read_text())
        download = (bundle / 'bitmap-download.zpl').read_text()
        for fid, paths in manifest['sources']['strikes'].items():
            source = Path('benchmarks/fonts') / paths[0]
            _, glyphs = unpack(source)
            for path in paths[1:]:
                glyphs.update(unpack(Path('benchmarks/fonts') / path)[1])
            record = download.split('~DBR:FC' + fid + '.FNT,', 1)[1].split('~DB', 1)[0].split('^CW', 1)[0]
            header = record.split(',', 7)
            self.assertEqual(int(header[2]), struct.unpack_from('<H', source.read_bytes(), 7)[0])
            parsed = list(re.finditer(r'#([0-9A-F]+)\.(\d+)\.(\d+)\.(-?\d+)\.(-?\d+)\.(\d+)\.([0-9A-F]*)', header[7]))
            self.assertEqual(len(parsed), len(glyphs))
            for match in parsed:
                cp, h, w, left, baseline_offset, advance, hexdata = match.groups()
                advance0, left0, top0, w0, h0, bits = glyphs[int(cp, 16)]
                self.assertEqual((int(left), -int(baseline_offset), int(advance)), (left0, top0, advance0))
                packed = bytes.fromhex(hexdata)
                expected = {(x, y) for y in range(h0) for x in range(w0) if bits[(y*w0+x)//8] & (128 >> ((y*w0+x)%8))}
                actual = {(x, y) for y in range(int(h)) for x in range(int(w)) if packed[y*((int(w)+7)//8)+x//8] & (128 >> (x%8))}
                self.assertEqual(actual, expected, (fid, cp))

    def test_bundle_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            for path in Path('comparison_fonts').iterdir():
                self.assertEqual(path.read_bytes(), (Path(tmp)/path.name).read_bytes(), path.name)

    def test_fixed_policy_does_not_change_source(self):
        for library in ('labelary', 'labelize', 'go', 'ffi', 'codyps-zpl-node'):
            metadata, preamble = configure('comparison_fonts', library)
            self.assertEqual(metadata['mode'], 'fixed')
            self.assertEqual(preamble, b'')

    def test_codyps_consumes_supplied_bitmap_strike(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / 'fonts'
            shutil.copytree('comparison_fonts', bundle, copy_function=shutil.copyfile)
            source = root / 'input.zpl'
            source.write_text('^XA^PW320^LL100^FO10,10^ADN,36,20^FDHello 123^FS^XZ')
            rows = []
            for substitute in (False, True):
                if substitute:
                    download = bundle / 'bitmap-download.zpl'
                    original = download.read_text()
                    changed = original.replace('^CWD,R:FCD.FNT', '^CWD,R:FCA.FNT')
                    self.assertNotEqual(original, changed)
                    download.write_text(changed)
                    manifest_path = bundle / 'manifest.json'
                    manifest = json.loads(manifest_path.read_text())
                    manifest['sha256'][download.name] = sha(download)
                    manifest_path.write_text(json.dumps(manifest))
                key = str(substitute)
                render(dict(source=str(source), sha256=sha(source), width=320, height=100,
                            library='library_codyps-zpl', row=dict(library='codyps-zpl'),
                            font_bundle=str(bundle)), root / (key + '.json'), root / key)
                row = json.loads((root / (key + '.json')).read_text())
                self.assertEqual(row['status'], 'rendered', row)
                self.assertEqual(row['font_control']['mode'], 'supplied-bitmap-and-callback')
                self.assertNotEqual(row['source_sha256'], row['submitted_source_sha256'])
                rows.append(row)
            self.assertNotEqual(rows[0]['pixel_sha256'], rows[1]['pixel_sha256'])

    def test_real_adapters_consume_fonts_without_changing_graphics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for library in ('codyps-zpl', 'forge', 'binarykits', 'zplr', 'zebrash', 'zebrash-ts', 'zpl-renderer-js'):
                for name, body in [('bitmap', '^FO10,10^ADN,36,20^FDHello 123^FS'),
                                   ('scalable', '^FO10,10^A0N,32,24^FDHello 123^FS'),
                                   ('graphics', '^FO10,10^GB80,40,3^FS')]:
                    with self.subTest(library=library, fixture=name):
                        source = root/'input.zpl'
                        source.write_text('^XA^PW320^LL100' + body + '^XZ')
                        rows = []
                        for controlled in (False, True):
                            key = f'{library}-{name}-{controlled}'
                            spec = dict(source=str(source), sha256=sha(source), width=320, height=100,
                                        library='library_'+library, row=dict(library=library))
                            if controlled:
                                spec['font_bundle'] = 'comparison_fonts'
                            render(spec, root/(key+'.json'), root/key)
                            row = json.loads((root/(key+'.json')).read_text())
                            self.assertEqual(row['status'], 'rendered', row)
                            self.assertEqual([row['width'], row['height']], [320, 100])
                            rows.append(row)
                        if name == 'graphics' or (library == 'codyps-zpl' and name == 'bitmap'):
                            # The supplied D strike matches codyps/zpl's resident pixels.
                            self.assertEqual(rows[0]['pixel_sha256'], rows[1]['pixel_sha256'])
                        else:
                            self.assertNotEqual(rows[0]['pixel_sha256'], rows[1]['pixel_sha256'])
                        self.assertNotIn('font_control', rows[0])
                        self.assertIn('font_control', rows[1])


if __name__ == '__main__':
    unittest.main()
