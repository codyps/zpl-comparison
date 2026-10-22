#!/usr/bin/env python3
"""Import immutable GX430t evidence and assemble the native 300-DPI campaign."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

from PIL import Image
from accuracy.pixels import gray, sha
from benchmarks import campaigns

ROOT = Path('references/gx430t-300-v1')
CASES = {
    'text': ['argument-font0-height-16', 'argument-font0-height-32', 'argument-font0-height-64',
             'argument-font0-rotation-R', 'argument-font0-rotation-I', 'argument-font0-rotation-B',
             'argument-font-A', 'argument-font-D', 'argument-utf8-accent', 'argument-block-J'],
    'layout': ['argument-ft-baseline', 'argument-layout-LH', 'argument-layout-LS',
               'argument-layout-LT', 'argument-layout-PO', 'argument-field-reverse'],
    'shapes': ['argument-box-thickness-1', 'argument-box-thickness-4', 'argument-box-round',
               'argument-box-white', 'argument-shape-GC-B', 'argument-shape-GE-B', 'argument-shape-GD-R'],
    'graphics': ['argument-graphic-hex', 'argument-graphic-binary', 'argument-graphic-Z64'],
    'barcodes': ['barcode-code128', 'barcode-code39', 'barcode-ean13', 'barcode-upca',
                 'barcode-qr', 'barcode-data_matrix', 'barcode-pdf417', 'barcode-maxicode4'],
}


def import_evidence(source, output=ROOT):
    """Copy original submitted bytes and firmware PNGs; never render references."""
    receipt = json.loads((source / 'provenance.json').read_text())
    if receipt['printer']['model'] != 'GX430t' or receipt['printer']['dpi'] != 300:
        raise ValueError('Expected identified GX430t 300-DPI evidence')
    indexed = {r['name']: r for r in receipt['cases']}
    names = ['control-start', 'control-end'] + [n for group in CASES.values() for n in group]
    for name in names:
        row = indexed[name]
        if row['status'] != 'captured':
            raise ValueError('Missing capture: ' + name)
        for suffix, key in [('.zpl', 'source_sha256'), ('.png', 'png_sha256')]:
            if sha(source / (name + suffix)) != row[key]:
                raise ValueError('Changed upstream evidence: ' + name)
        if list(Image.open(source / (name + '.png')).size) != row['dimensions']:
            raise ValueError('Changed capture dimensions')
    if not (gray(source / 'control-start.png') == gray(source / 'control-end.png')).all():
        raise ValueError('Repeated control changed')
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name in ['provenance.json', 'reset.zpl', 'config-start.html', 'status-start.html'] + [n + ext for n in names for ext in ['.zpl', '.png']]:
        shutil.copyfile(source / name, output / name)
        files[name] = sha(output / name)
    cases = []
    for group, names in CASES.items():
        for name in names:
            row = indexed[name]
            width, height = row['dimensions']
            cases.append(dict(name=name, group=group, width=width, height=height,
                              sha256=row['source_sha256'], reference_sha256=row['png_sha256'],
                              source=str(output / (name + '.zpl')), reference=str(output / (name + '.png')),
                              commands=sorted(set(c.decode() for c in re.findall(rb'\^[A-Z][A-Z0-9]', (source / (name + '.zpl')).read_bytes().split(b'^PW', 1)[-1]))),
                              capture=row, notes='GX430t 300 DPI / 12 dots per mm; V56.17.17Z HTTP Preview Label. Original submitted reset and fixture bytes. Native 832 × 2558 canvas; LL is ignored by this preview.'))
    manifest = dict(schema=1, device=receipt['printer'], method='HTTP Preview Label; not physical print/scan',
                    upstream=dict(repository='https://github.com/codyps/zpl', commit=receipt['repository_commit'],
                                  path='zpl/tests/fixtures/gx430t-300-v1/main', working_tree=receipt['working_tree']),
                    captured_utc=receipt['started'], capture_finished_utc=receipt['finished'],
                    repeat_pixels_equal=True, cases=cases, files=files)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def verify(root=ROOT):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if sha(root / name) != digest:
            raise ValueError('Changed GX430t evidence: ' + name)
    receipt = json.loads((root / 'provenance.json').read_text())
    if manifest['device'] != receipt['printer'] or manifest['device']['dpi'] != 300:
        raise ValueError('GX430t identity changed')
    a, b = gray(root / 'control-start.png'), gray(root / 'control-end.png')
    if a.shape != b.shape or not (a == b).all() or not (a < 128).any():
        raise ValueError('GX430t repeated control is unstable or blank')
    indexed = {r['name']: r for r in receipt['cases']}
    for case in manifest['cases']:
        row = indexed[case['name']]
        if (case['sha256'] != row['source_sha256'] or case['reference_sha256'] != row['png_sha256']
                or [case['width'], case['height']] != row['dimensions']
                or sha(Path(case['source'])) != case['sha256'] or sha(Path(case['reference'])) != case['reference_sha256']):
            raise ValueError('GX430t case differs from capture receipt')
    return manifest


def report(libraries):
    from gx430t_labelary import OUTPUT as service_root, validate as validate_labelary

    manifest = verify()
    service = validate_labelary()
    output = Path('docs/benchmarks/gx430t-300dpi')
    data = campaigns.assemble('gx430t-300dpi', manifest['cases'], libraries, '_gx430t_rows', output,
                              manifests={str(ROOT / 'manifest.json'): sha(ROOT / 'manifest.json'),
                                         str(service_root / 'captures.json'): sha(service_root / 'captures.json')},
                              printer=manifest['device'], captured_utc=manifest['captured_utc'],
                              labelary=dict(dpmm=service['dpmm'], dpi=service['dpi'],
                                            started_utc=service['started_utc'], completed_utc=service['completed_utc'],
                                            identity=service['identity']))
    campaigns.verify(data, Path.cwd())
    campaigns.write(data, output)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--report']:
        report(sys.argv[2:])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--import-from', type=Path)
        args = parser.parse_args()
        if args.import_from:
            import_evidence(args.import_from)
        print(f"Verified {len(verify()['cases'])} GX430t 300-DPI cases and repeated controls")
