#!/usr/bin/env python3
"""Explicit RAM font installation and preview-only capture; never run by Bazel."""
import argparse
import copy
import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'benchmarks/accuracy'))
from capture import preview_reset, SameOrigin
sys.path.insert(0, str(ROOT / 'build'))
from font_profile import configure

HOSTS = {'zd621': 'http://d7j211001302.bed.einic.org/',
         'zq610': 'http://xxzmj230802993.bed.einic.org/'}
STANDARD = ['benchmarks/accuracy/' + n + '/manifest.json' for n in
            ['reference', 'conformance-reference', 'external-reference', 'layout-reference']]
STANDARD += ['references/public-zd621-20261002/manifest.json']
BARCODES = 'references/barcodes-zd621-v1/manifest.json'
PAIRED = 'references/zq610-plus-v1/manifest.json'
CANDIDATES = 'references/zq610-candidates/manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def inventory():
    manifests = {p: json.loads((ROOT / p).read_text()) for p in STANDARD + [BARCODES, PAIRED, CANDIDATES]}
    cases = {}
    def add(source, reference, digest, width, height, printer, ram=False):
        data = (ROOT / source).read_bytes()
        if sha(data) != digest:
            raise ValueError('Source hash mismatch: ' + source)
        value = dict(source=source, reference=reference, source_sha256=digest,
                     width=width, height=height, printer=printer, ram_resources=ram)
        if reference in cases and cases[reference] != value:
            raise ValueError('Inconsistent reference: ' + reference)
        cases[reference] = value
    for path in STANDARD:
        for row in manifests[path]['cases']:
            stem = str(Path(path).parent / row['name'])
            add(stem + '.zpl', stem + '.png', row['zpl_sha256'], row['width'], row['height'],
                'zd621', row.get('capture_scope') == 'ram-resources')
    for name, row in manifests[BARCODES]['cases'].items():
        stem = str(Path(BARCODES).parent / name)
        add(stem + '.zpl', stem + '.png', row['zpl_sha256'], manifests[BARCODES]['width'], 1218, 'zd621')
    for name, row in manifests[PAIRED]['cases'].items():
        for printer, status in row['status'].items():
            if status.get('status') != 'captured':
                continue
            stem = str(Path(PAIRED).parent / name / printer)
            add(stem + '.zpl', stem + '.png', status['submitted_sha256'],
                *status['measurement']['dimensions'], printer)
    for row in manifests[CANDIDATES]['cases']:
        add(row['source'], row['reference'], row['sha256'], row['width'], row['height'], 'zq610')
    return manifests, list(cases.values())


def fonts(bundle):
    policy, _ = configure(bundle, 'zplr')  # verifies every bundled hash
    policy.update(mode='supplied-printer-ram', note='Recovered native bitmap fonts via ~DB; shared TrueType bytes via ~DY. Per-format ^CW aliases; GS and some captions retain resident fonts.')
    bitmap = (bundle / 'bitmap-download.zpl').read_bytes()
    aliases = b''.join(re.findall(rb'\^CW[^\^~]*', bitmap))
    uploads = re.sub(rb'\^CW[^\^~]*', b'', bitmap)
    names = re.findall(rb'~DB([^,]+),', uploads)
    for name, filename in [('FC0', '0.ttf'), ('TT0003M_', 'Swiss.ttf')]:
        data = (bundle / filename).read_bytes()
        uploads += f'~DYR:{name},B,T,{len(data)},,'.encode() + data
        names.append(('R:' + name + '.TTF').encode())
    return policy, uploads, aliases, [n.decode() for n in names]


class Printer:
    def __init__(self, origin):
        self.origin = origin
        self.host = urllib.parse.urlsplit(origin).hostname
        self.opener = urllib.request.build_opener(SameOrigin())

    def fetch(self, path, data=None):
        url = urllib.parse.urljoin(self.origin, path)
        if urllib.parse.urlsplit(url)[:2] != urllib.parse.urlsplit(self.origin)[:2]:
            raise ValueError('Cross-origin request')
        with self.opener.open(urllib.request.Request(url, data=data), timeout=30) as response:
            body = response.read(16 * 1024 * 1024 + 1)
        if len(body) > 16 * 1024 * 1024:
            raise ValueError('Oversize response')
        return body

    def raw(self, data):
        with socket.create_connection((self.host, 9100), timeout=30) as connection:
            connection.sendall(data)

    def preview(self, data):
        form = urllib.parse.urlencode(dict(dev='R', oname='FCAPTURE', otype='ZPL',
                                          data=data, prev='Preview Label', username='', pw='')).encode()
        page = self.fetch('zpl', form)
        match = re.search(rb'<IMG\s+SRC="([^"]+)"', page, re.I)
        if not match:
            raise ValueError('No preview image')
        png = self.fetch(html.unescape(match[1].decode()))
        image = Image.open(io.BytesIO(png))
        image.load()
        if image.format != 'PNG':
            raise ValueError('Not a PNG')
        return png, image


def submission(case, aliases):
    data = (ROOT / case['source']).read_bytes()
    if sha(data) != case['source_sha256'] or b'\0' in data:
        raise ValueError('Changed or binary source: ' + case['source'])
    start = data.rfind(b'^XA') if case['ram_resources'] else data.find(b'^XA')
    if start < 0 or (start != 0 and not case['ram_resources']):
        raise ValueError('Unexpected source preamble')
    setup = data[:start]
    if setup and (setup.count(b'^DFR:CMPEX.ZPL') != 1 or setup.count(b'^XZ') != 1):
        raise ValueError('Unreviewed RAM setup')
    prefix = f"^PW{case['width']}^LL{case['height']}".encode() + preview_reset()[3:-3] + aliases
    return setup, b'^XA' + prefix + data[start + 3:]


def pixels(png):
    image = Image.open(io.BytesIO(png)).convert('RGBA')
    return image.size, image.tobytes()


def restart(printer, record, path):
    """Only called by the explicitly requested --restart-after-capture workflow."""
    expected = {'zd621': 'D7J211001302', 'zq610': 'XXZMJ230802993'}
    label = next(key for key, origin in HOSTS.items() if origin == printer.origin)
    with socket.create_connection((printer.host, 9100), timeout=5) as connection:
        connection.settimeout(5)
        connection.sendall(b'! U1 getvar "device.unique_id"\r\n')
        serial = connection.recv(128).strip().strip(b'"').decode()
    if serial != expected[label]:
        raise ValueError('Restart serial mismatch')
    event = dict(serial=serial, requested_utc=now(), method='! U1 do "device.reset" ""', status='requested')
    record.setdefault('restarts', []).append(event)
    save(path, record)
    printer.raw(b'! U1 do "device.reset" ""\r\n')
    event['status'] = 'sent'
    save(path, record)
    for attempt in range(30):
        time.sleep(3)
        try:
            with printer.opener.open(printer.origin + 'index.html', timeout=5) as response:
                home = response.read(65536)
            if ('<H2>' + serial + '</H2>').encode() not in home:
                continue
        except (OSError, urllib.error.URLError):
            continue
        event.update(status='recovered', verified_utc=now())
        save(path, record)
        print('Restart and HTTP identity verified:', serial, flush=True)
        return
    raise TimeoutError('Printer did not recover after restart')


def discard_interrupted(out, record):
    """Keep aborted-session evidence, but require new controls before scoring it."""
    sid = len(record['sessions'])
    session = record['sessions'][-1]
    if session['status'] != 'interrupted' or not record.get('inflight'):
        raise ValueError('Only an interrupted preview can be recovered')
    key = record['inflight']
    attempts = sum(r['reference'] == key for r in record.get('interrupted_requests', []))
    if attempts >= 2:
        raise ValueError('Repeatedly stalled fixture requires inspection: ' + key)
    session['status'] = 'discarded'
    session['discarded_cases'] = {}
    for reference, row in list(record['cases'].items()):
        if row['session'] != sid:
            continue
        dest = out / 'sessions' / str(sid) / 'discarded' / reference
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / 'overlay' / reference, dest)
        session['discarded_cases'][reference] = record['cases'].pop(reference)
    record.setdefault('interrupted_requests', []).append(dict(reference=record.pop('inflight'),
        submitted_sha256=record.pop('inflight_sha256'), session=sid))
    record['retry_first'] = key


def capture(args):
    manifests, cases = inventory()
    policy, upload, aliases, names = fonts(args.bundle)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'capture.json'
    record = json.loads(path.read_text()) if path.exists() else dict(schema=1, status='incomplete', started_utc=now(),
        font_control=policy, method='RAM ~DB recovered bitmaps and binary ~DY TrueType; HTTP Preview Label',
        upload_sha256=sha(upload), cases={}, sessions=[], source_manifests={p: sha((ROOT / p).read_bytes()) for p in manifests})
    if record['font_control'] != policy or record['source_manifests'] != {p: sha((ROOT / p).read_bytes()) for p in manifests}:
        raise ValueError('Capture inputs changed')
    if record['status'] == 'complete':
        verify(out, args.bundle)
        export(out, manifests, record, aliases)
        print('Existing capture is complete and verified', flush=True)
        return
    if record.get('inflight'):
        if not getattr(args, 'restart_after_capture', False):
            raise ValueError('Previous request interrupted; inspect printer before retry: ' + record['inflight'])
        discard_interrupted(out, record)
    for key, row in record['cases'].items():
        if sha((out / 'overlay' / key).read_bytes()) != row['png_sha256']:
            raise ValueError('Saved preview changed')
    save(path, record)
    save(out / 'catalog.json', {'_capture_status': 'incomplete'})
    for label, origin in HOSTS.items():
        remaining = [c for c in cases if c['printer'] == label and c['reference'] not in record['cases']]
        remaining.sort(key=lambda c: c['reference'] != record.get('retry_first'))
        if not remaining:
            continue
        if getattr(args, 'max_cases', 0):
            remaining = remaining[:args.max_cases]
        printer = Printer(origin)
        if getattr(args, 'restart_after_capture', False):
            restart(printer, record, path)
        home, config = printer.fetch('index.html'), printer.fetch('config.html')
        identity = dict(model=re.search(rb'ZTC [^<\r\n]+', home)[0].decode(),
                        serial=re.search(rb'<H2>([^<]+)</H2>', home)[1].decode(),
                        firmware=re.search(rb'(V[0-9.]+[A-Z]?)\s*(?:&lt;-)?\s+FIRMWARE', config)[1].decode(), host=origin)
        if ('ZD621' if label == 'zd621' else 'ZQ610 Plus') not in identity['model']:
            raise ValueError('Wrong printer')
        directory = printer.fetch('dir?dev=*')
        existing = {fid: name for ids, name in re.findall(rb'<TR>\s*<TD[^>]*>(.*?)</TD>\s*<TD[^>]*>(.*?)</TD>', directory, re.S)
                    for fid in ids.decode() if fid in '0ABCDEFGHPQRSTUV' and b':' in name}
        restore = b''.join(b'^CW' + fid.encode() + b',' + existing.get(fid,
            b'Z:0.TTF' if fid == '0' else ('Z:' + fid + '.FNT').encode()) for fid in '0ABCDEFGHPQRSTUV')
        # Include every changed alias in the control, so cleanup is observable.
        control = b'^XA^PW384^LL600' + preview_reset()[3:-3] + b''.join(
            f'^FO10,{10+i*30}^A{fid}N,20,12^FDAb12^FS'.encode() for i, fid in enumerate('0ABCDEFGHPQRSTUV')) + b'^XZ'
        original, _ = printer.preview(control)
        before = original if getattr(args, 'restart_after_capture', False) else printer.preview(control[:3] + restore + control[3:])[0]
        session = dict(printer=label, identity=identity, started_utc=now(), status='incomplete', upload_sha256=sha(upload))
        session['resident_alias_normalization_pixels_equal'] = pixels(original) == pixels(before)
        record['sessions'].append(session)
        session_id = len(record['sessions'])
        evidence = out / 'sessions' / str(session_id)
        evidence.mkdir(parents=True)
        (evidence / 'directory-before.html').write_bytes(directory)
        (evidence / 'restore.zpl').write_bytes(restore)
        (evidence / 'control.zpl').write_bytes(control)
        (evidence / 'resident-original.png').write_bytes(original)
        (evidence / 'before.png').write_bytes(before)
        save(path, record)
        network_failed = False
        try:
            printer.raw(upload)
            # Mobile firmware compiles downloads asynchronously; do not preview
            # while the font download is still queued behind the raw socket.
            for attempt in range(30):
                time.sleep(2)
                installed = printer.fetch('dir?dev=R')
                (evidence / 'directory-installed.html').write_bytes(installed)
                if all(name.encode() in installed for name in names):
                    break
                print(f'{label}: waiting for font installation ({attempt + 1}/30)', flush=True)
            else:
                raise ValueError('Font missing from printer RAM directory')
            time.sleep(2)
            controlled = control[:3] + aliases + control[3:]
            first, _ = printer.preview(controlled)
            (evidence / 'controlled-start.png').write_bytes(first)
            if pixels(first) == pixels(before):
                raise ValueError('Supplied font control did not change')
            restored = before if getattr(args, 'restart_after_capture', False) else printer.preview(control[:3] + restore + control[3:])[0]
            if pixels(restored) != pixels(before):
                session.update(status='preflight-failed', error='Resident implicit T/U/V aliases differ after explicit restoration; no corpus inputs captured')
                raise ValueError('Font restoration preflight failed')
            for index, case in enumerate(remaining):
                setup, data = submission(case, aliases)
                if setup:
                    printer.raw(setup)
                key = case['reference']
                # Persist the inflight source before any request; never silently replay a timeout.
                if record.get('inflight'):
                    raise ValueError('Previous request interrupted; inspect printer before retry: ' + record['inflight'])
                submitted_path = 'submitted/' + key[:-4] + '.zpl'
                submitted = out / submitted_path
                submitted.parent.mkdir(parents=True, exist_ok=True)
                submitted.write_bytes(data)
                record['inflight'] = key
                record['inflight_sha256'] = sha(data)
                save(path, record)
                png, image = printer.preview(data)
                target = out / 'overlay' / key
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(png)
                record['cases'][key] = dict(case, png_sha256=sha(png), submitted_sha256=sha(data),
                    submitted=submitted_path, printer_dimensions=list(image.size), captured_utc=now(), session=session_id)
                record.pop('inflight')
                record.pop('inflight_sha256')
                save(path, record)
                print(f'{label} {index+1}/{len(remaining)} {key} {image.size}', flush=True)
                time.sleep(args.interval)
            last, _ = printer.preview(controlled)
            (evidence / 'controlled-end.png').write_bytes(last)
            session['repeat_pixels_equal'] = pixels(first) == pixels(last)
            if not session['repeat_pixels_equal']:
                raise ValueError('Repeated font control changed')
            session['status'] = 'complete'
        except (TimeoutError, urllib.error.URLError) as error:
            network_failed = True
            session.update(status='interrupted', error=str(error), restoration_status='not attempted after network error')
            raise
        finally:
            # Do not queue another POST behind a potentially still-running preview.
            if getattr(args, 'restart_after_capture', False):
                restart(printer, record, path)
                session['restoration_method'] = 'verified device.reset'
                session['restoration_status'] = 'verified after restart'
                after, _ = printer.preview(control)
                (evidence / 'after.png').write_bytes(after)
                session['restored_pixels_equal'] = pixels(before) == pixels(after)
            elif not network_failed:
                after, _ = printer.preview(control[:3] + restore + control[3:])
                (evidence / 'after.png').write_bytes(after)
                session['restored_pixels_equal'] = pixels(before) == pixels(after)
            session['finished_utc'] = now()
            save(path, record)
            if not network_failed and not session['restored_pixels_equal']:
                raise ValueError('Printer font restoration control changed')
    if len(record['cases']) != len(cases):
        print(f"Verified batch saved: {len(record['cases'])}/{len(cases)} previews; run again for the next batch", flush=True)
        return
    if any(s['status'] != 'complete' or not s.get('repeat_pixels_equal') or not s.get('restored_pixels_equal') for s in record['sessions'] if s['status'] not in {'preflight-failed', 'discarded'}):
        raise ValueError('An incomplete or unstable session requires recapture before export')
    record.update(status='complete', finished_utc=now())
    save(path, record)
    verify(out, args.bundle)
    export(out, manifests, record, aliases)


def verify(out, bundle):
    """Verify live capture evidence, including submitted bytes and control pixels."""
    record = json.loads((out / 'capture.json').read_text())
    manifests, cases = inventory()
    policy, upload, aliases, _ = fonts(bundle)
    if record['status'] != 'complete' or record.get('inflight'):
        raise ValueError('Incomplete printer capture')
    if record['font_control'] != policy or record['upload_sha256'] != sha(upload):
        raise ValueError('Printer font bundle mismatch')
    if record['source_manifests'] != {p: sha((ROOT / p).read_bytes()) for p in manifests}:
        raise ValueError('Printer source manifests changed')
    if set(record['cases']) != {c['reference'] for c in cases}:
        raise ValueError('Incomplete reference coverage')
    for case in cases:
        row = record['cases'][case['reference']]
        setup, submitted = submission(case, aliases)
        if any(row[k] != v for k, v in case.items()):
            raise ValueError('Capture input changed')
        if sha(submitted) != row['submitted_sha256'] or (out / row['submitted']).read_bytes() != submitted:
            raise ValueError('Submitted source mismatch')
        png = (out / 'overlay' / case['reference']).read_bytes()
        if sha(png) != row['png_sha256'] or list(pixels(png)[0]) != row['printer_dimensions']:
            raise ValueError('Captured raster mismatch')
        if record['sessions'][row['session'] - 1]['printer'] != case['printer']:
            raise ValueError('Wrong capture printer')
    for index, session in enumerate(record['sessions'], 1):
        if session['status'] in {'preflight-failed', 'discarded'}:
            if any(row['session'] == index for row in record['cases'].values()):
                raise ValueError('Corpus capture from failed preflight')
            continue
        if session['status'] != 'complete' or not session.get('repeat_pixels_equal') or not session.get('restored_pixels_equal'):
            raise ValueError('Unstable capture session')
        evidence = out / 'sessions' / str(index)
        before, first, last, after = [pixels((evidence / (name + '.png')).read_bytes()) for name in
                                     ['before', 'controlled-start', 'controlled-end', 'after']]
        if first != last or before != after or first == before:
            raise ValueError('Font or restoration control failed')
    return record


def export(out, manifests, record, aliases):
    """Overlay only captured rasters and their manifests, preserving source fixtures."""
    if record['status'] != 'complete':
        raise ValueError('Cannot export incomplete captures')
    identities = {s['printer']: dict(s['identity'], dpi=203) for s in record['sessions']}
    provenance = dict(manifest='references/font-controlled/capture.json',
                      capture_sha256=sha((json.dumps(record, indent=2, sort_keys=True) + '\n').encode()),
                      bundle_sha256=record['font_control']['bundle_sha256'], captured_utc=record['finished_utc'],
                      method=record['method'])
    def captured(path):
        return record['cases'][path]
    for path, original in manifests.items():
        m = copy.deepcopy(original)
        m['font_capture'] = provenance
        if path in STANDARD or path == BARCODES:
            device = identities['zd621']
            m.update(device=device['model'], firmware=device['firmware'], host=device['host'])
        if path in STANDARD:
            for historical in ['refresh_batches', 'corpus_updates', 'resumed_utc']:
                m.pop(historical, None)
        if path in STANDARD:
            m.update(captured_utc=record['finished_utc'], method=record['method'], status='complete', repeat_pixels_equal=True,
                     preview_reset_zpl=(preview_reset()[:-3] + aliases + b'^XZ').decode())
            for row in m['cases']:
                c = captured(str(Path(path).parent / (row['name'] + '.png')))
                row.update({k: c[k] for k in ['png_sha256', 'printer_dimensions', 'submitted_sha256', 'captured_utc']})
                row['font_capture'] = provenance
                row['submission_mode'] = 'ram-setup-inline-reset-canvas' if c['ram_resources'] else 'inline-reset-canvas'
                if c['ram_resources']:
                    row['setup_sha256'] = sha(submission(c, aliases)[0])
        elif path == BARCODES:
            m.update(captured_utc=record['finished_utc'], method=record['method'],
                     preview_reset_zpl=(preview_reset()[:-3] + aliases + b'^XZ').decode())
            m.pop('captured_unix_seconds', None)
            for name, row in m['cases'].items():
                key = str(Path(path).parent / (name + '.png'))
                c = captured(key)
                row['printer_png_sha256'] = c['png_sha256']
                image = Image.open(out / 'overlay' / key).convert('L')
                row['printer'] = dict(width=image.width, height=image.height,
                    ink=image.point(lambda value: 255 if value < 128 else 0).histogram()[255], pixels_sha256=sha(image.tobytes()))
                row['font_capture'] = dict(provenance, submitted_sha256=c['submitted_sha256'])
        elif path == PAIRED:
            m['printers'] = identities
            for name, row in m['cases'].items():
                for printer, status in row['status'].items():
                    key = str(Path(path).parent / name / (printer + '.png'))
                    if key in record['cases']:
                        c = captured(key)
                        status['font_capture'] = dict(provenance, submitted_sha256=c['submitted_sha256'], captured_utc=c['captured_utc'])
                        image = Image.open(out / 'overlay' / key).convert('L')
                        mask = image.point(lambda value: 255 if value < 128 else 0)
                        status['measurement'] = dict(dimensions=c['printer_dimensions'], bbox=mask.getbbox(), ink=mask.histogram()[255])
                        m['files'][name + '/' + printer + '.png'] = c['png_sha256']
        elif path == CANDIDATES:
            m['printer'] = identities['zq610']
            for row in m['cases']:
                row['png_sha256'] = captured(row['reference'])['png_sha256']
            m['paired_manifest_sha256'] = sha((out / 'overlay' / PAIRED).read_bytes())
        save(out / 'overlay' / path, m)
    save(out / 'catalog.json', {'_capture_status': 'complete', **{p: json.loads((out / 'overlay' / p).read_text()) for p in manifests}})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'bazel-bin/comparison_fonts')
    parser.add_argument('--output', type=Path, default=ROOT / 'references/font-controlled')
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--max-cases', type=int, default=20, help='Bound each printer session and repeat its control before continuing in another invocation')
    parser.add_argument('--restart-after-capture', action='store_true', help='Explicitly authorize serial-verified restarts before and after sessions, including timeout recovery')
    parser.add_argument('--verify', action='store_true', help='Verify and export existing captures without contacting printers')
    args = parser.parse_args()
    if args.interval < 0 or args.max_cases < 0:
        parser.error('Use a nonnegative interval and batch limit')
    if args.verify:
        record = verify(args.output, args.bundle)
        export(args.output, inventory()[0], record, fonts(args.bundle)[2])
        print('Verified', len(record['cases']), 'font-controlled printer previews')
    else:
        capture(args)
