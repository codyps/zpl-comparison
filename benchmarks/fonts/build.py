"""Build deterministic TrueType carriers for recovered strikes and Heros substitutes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
EPOCH = 2082844800  # 1970-01-01 in OpenType's 1904 epoch


def unpack(path):
    data = path.read_bytes()
    magic, fid, height, width, dpi, count = struct.unpack_from('<4scHHHH', data)
    if magic not in (b'ZBF1', b'ZBF2'):
        raise ValueError('Unsupported strike')
    offset, glyphs = 13, {}
    fmt = '<B HhhHH' if magic == b'ZBF1' else '<I HhhHH'
    for _ in range(count):
        cp, advance, left, top, w, h = struct.unpack_from(fmt, data, offset)
        offset += struct.calcsize(fmt)
        size = (w * h + 7) // 8
        bits = data[offset:offset + size]
        if len(bits) != size or cp in glyphs:
            raise ValueError('Invalid strike glyph')
        offset += size
        glyphs[cp] = (advance, left, top, w, h, bits)
    if offset != len(data):
        raise ValueError('Trailing strike bytes')
    return height, glyphs


def finish(builder, name, path, ascent, descent, notices=None):
    builder.setupHorizontalHeader(ascent=ascent, descent=descent)
    builder.setupNameTable(dict(familyName=name, styleName='Regular', uniqueFontIdentifier=name + '-1', fullName=name, psName=name, **(notices or {})))
    builder.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
                    usWinAscent=ascent, usWinDescent=-descent)
    builder.setupPost()
    builder.setupMaxp()
    builder.font['head'].created = builder.font['head'].modified = EPOCH
    builder.font.recalcTimestamp = False
    builder.save(path)


def bitmap(paths, name, target):
    height, glyphs = unpack(paths[0])
    for path in paths[1:]:
        h, extra = unpack(path)
        if h != height:
            raise ValueError('Strike height mismatch')
        glyphs.update(extra)
    # Integral font units preserve every pixel edge and advance without rounding.
    unit = 16
    order = ['.notdef'] + [f'u{cp:06X}' for cp in sorted(glyphs)]
    builder = FontBuilder(height * unit, isTTF=True)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({cp: f'u{cp:06X}' for cp in glyphs})
    outlines = {'.notdef': TTGlyphPen(None).glyph()}
    metrics = {'.notdef': (height * unit // 2, 0)}
    for cp, (advance, left, top, w, h, bits) in glyphs.items():
        pen = TTGlyphPen(None)
        for y in range(h):
            x = 0
            while x < w:
                if not (bits[(y*w+x)//8] & (128 >> ((y*w+x) % 8))):
                    x += 1
                    continue
                start = x
                while x < w and bits[(y*w+x)//8] & (128 >> ((y*w+x) % 8)):
                    x += 1
                x0, x1 = (left+start)*unit, (left+x)*unit
                y0, y1 = -(top+y+1)*unit, -(top+y)*unit
                pen.moveTo((x0, y0)); pen.lineTo((x0, y1))
                pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()
        key = f'u{cp:06X}'
        outlines[key] = pen.glyph()
        metrics[key] = (advance*unit, left*unit)
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics(metrics)
    ascent = max(-g[2] for g in glyphs.values()) * unit
    descent = min(0, min(-g[2]-g[4] for g in glyphs.values())) * unit
    finish(builder, name, target, ascent, descent)


def bitmap_download(paths, fid):
    height, glyphs = unpack(paths[0])
    for path in paths[1:]:
        glyphs.update(unpack(path)[1])
    baseline = max(-g[2] for g in glyphs.values())
    width = struct.unpack_from('<H', paths[0].read_bytes(), 7)[0]
    name = 'R:FC' + fid + '.FNT'
    parts = [f'~DB{name},N,{height},{width},{baseline},{glyphs[32][0]},{len(glyphs)},Recovered,']
    for cp, (advance, left, top, w, h, bits) in sorted(glyphs.items()):
        # ~DB requires nonempty cells, including the blank space glyph.
        rw, rh = max(1, w), max(1, h)
        row_bytes = (rw + 7) // 8
        packed = bytearray(row_bytes * rh)
        for y in range(h):
            for x in range(w):
                if bits[(y*w+x)//8] & (128 >> ((y*w+x) % 8)):
                    packed[y*row_bytes+x//8] |= 128 >> (x % 8)
        parts.append(f'#{cp:04X}.{rh}.{rw}.{left}.{-top}.{advance}.' + packed.hex().upper())
    if len(fid) == 1:
        parts.append(f'^CW{fid},{name}')
    return ''.join(parts)


def outline(source, name, target):
    original = TTFont(source)
    builder = FontBuilder(original['head'].unitsPerEm, isTTF=True)
    builder.setupGlyphOrder(original.getGlyphOrder())
    builder.setupCharacterMap(original.getBestCmap())
    glyph_set = original.getGlyphSet()
    glyphs = {}
    for key in original.getGlyphOrder():
        pen = TTGlyphPen(glyph_set)
        glyph_set[key].draw(Cu2QuPen(pen, max_err=1.0, reverse_direction=True))
        glyphs[key] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(original['hmtx'].metrics)
    notices = {key: value for key, number in [('copyright', 0), ('trademark', 7), ('manufacturer', 8), ('designer', 9), ('licenseDescription', 13), ('licenseInfoURL', 14)] if (value := original['name'].getDebugName(number))}
    finish(builder, name, target, original['hhea'].ascent, original['hhea'].descent, notices)


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'sources.json').read_text())
    for relative, digest in manifest['sha256'].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError('Font source hash mismatch: ' + relative)
    (output / 'GUST-LICENSE.txt').write_bytes((ROOT / 'source/GUST-LICENSE.txt').read_bytes())
    mapping = {}
    downloads = []
    for fid, paths in manifest['strikes'].items():
        filename = fid + '.ttf'
        bitmap([ROOT / p for p in paths], 'RecoveredZebra-' + fid, output / filename)
        mapping[fid] = filename
        downloads.append(bitmap_download([ROOT / p for p in paths], fid))
    mapping['C'] = mapping['D']
    downloads.append('^CWC,R:FCD.FNT^CW0,R:FC0.TTF')
    (output / 'bitmap-download.zpl').write_text(''.join(downloads))
    outline(ROOT / 'source/heros-cn-bold.otf', 'ComparisonHerosCondensedBold', output / '0.ttf')
    outline(ROOT / 'source/heros-regular.otf', 'ComparisonHerosRegular', output / 'Swiss.ttf')
    mapping['0'] = '0.ttf'
    mapping['TT0003M_'] = 'Swiss.ttf'
    result = dict(schema=1, fonts=mapping, sources=manifest,
                  sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(p for p in output.iterdir() if p.suffix in {'.ttf', '.zpl', '.txt'})})
    (output / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
