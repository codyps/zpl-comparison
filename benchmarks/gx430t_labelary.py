#!/usr/bin/env python3
"""Capture 12-dpmm Labelary responses for the exact GX430t source/native canvas.

Only --capture contacts the service. Normal report builds verify saved responses.
"""
import argparse
from pathlib import Path

import gx430t
import labelary

OUTPUT = gx430t.ROOT / 'labelary'


def inputs():
    return [dict(suite='gx430t-300dpi', name=c['name'], source=c['source'],
                 sha256=c['sha256'], width=c['width'], height=c['height'], validity='valid')
            for c in gx430t.verify()['cases']]


def validate(dest=OUTPUT):
    original = labelary.inputs
    try:
        labelary.inputs = inputs
        return labelary.validate(dest, dpmm=12)
    finally:
        labelary.inputs = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.capture:
        labelary.inputs = inputs
        labelary.capture(args.output, extend=(args.output / 'captures.json').exists(), dpmm=12)
    data = validate(args.output)
    print('Verified', len(data['cases']), 'Labelary responses at 12 dpmm / 300 DPI')


if __name__ == '__main__':
    main()
