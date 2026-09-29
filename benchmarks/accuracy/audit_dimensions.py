#!/usr/bin/env python3
"""Inventory every tracked ZPL canvas, including preserved diagnostic evidence.

Only ordinary preview comparisons must have 64-dot-aligned widths. Historical
sources and explicit boundary tests describe the behavior being investigated;
local-only timing/invalid probes are never submitted to the preview service.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[2]


def audit():
    active = {}
    for suite in ('render-conformance', 'layout-accuracy', 'external-zpl'):
        directory = REPO / 'test-data' / suite
        for row in json.loads((directory / 'manifest.json').read_text())['cases']:
            active[str((directory / row['file']).relative_to(REPO))] = row
    paths = subprocess.check_output(['git', 'ls-files', '*.zpl'], cwd=REPO, text=True).splitlines()
    counts, unaligned, failures = Counter(), [], []
    for name in paths:
        source = (REPO / name).read_bytes()
        widths = [int(v) for v in re.findall(rb'\^PW(\d+)', source)]
        lengths = [int(v) for v in re.findall(rb'\^LL(\d+)', source)]
        if name in active:
            role = 'ordinary-comparison'
            row = active[name]
            if row['width'] % 64 or any(w % 64 for w in widths):
                failures.append(name)
        elif name.startswith(('benchmarks/fixtures/', 'test-data/invalid-zpl/')):
            role = 'offline-only-performance-or-invalid-input'
        elif name.startswith(('references/zq610-plus-v1/', 'references/preview-width-audit-')):
            role = 'explicit-device-canvas-boundary-diagnostic'
        elif name.startswith(('references/preview-state-audit-', 'references/upstream-zd621/superseded-')):
            role = 'historical-audit-evidence'
        elif name.startswith('test-data/external-zpl/'):
            role = 'preserved-upstream-original'
        else:
            role = 'printer-capture-or-imported-reference'
            if any(w % 64 for w in widths):
                failures.append(name)
        counts[role] += 1
        if any(w % 64 for w in widths):
            unaligned.append(dict(file=name, role=role, widths=widths, lengths=lengths))
    return dict(tracked_zpl_files=len(paths), roles=dict(sorted(counts.items())),
                ordinary_manifest_cases=len(active), unaligned=unaligned, failures=failures,
                policy='ZD621 preview widths use multiples of 64. LL is not rounded to 64; preserve requested heights. ZQ610 canvas/width diagnostics and historical originals retain exact bytes. Offline-only performance and invalid-input probes do not have printer comparisons.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = audit()
    contents = json.dumps(data, indent=2) + '\n'
    if args.output:
        args.output.write_text(contents)
    else:
        print(contents, end='')
    if data['failures']:
        raise SystemExit('Unaligned ordinary comparisons or current capture sources')


if __name__ == '__main__':
    main()
