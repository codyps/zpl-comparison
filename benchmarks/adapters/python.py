"""Python ZPL builder; API source pinned in sources.lock.json."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_work/python-zpl"))
import zpl

mode, file, count, output = sys.argv[1:]
assert mode == "generate"
fields = int(Path(file).read_text())
n = int(count)
assert n > 0


def operation():
    label = zpl.Label(37.5, 50, dpmm=8)
    for i in range(fields):
        label.origin((10 + i % 4 * 95) / 8, (10 + i // 4 * 22) / 8)
        label.write_text(f"Item {i:02}", char_height=2)
        label.endorigin()
    return label.dumpZPL()


warmup = time.perf_counter()
warmed = 0
while warmed < 3 or time.perf_counter() - warmup < 0.25:
    operation()
    warmed += 1
start = time.perf_counter_ns()
checksum = 0
for _ in range(n):
    result = operation()
    checksum += len(result)
ns = time.perf_counter_ns() - start
Path(output).write_text(result)
print(json.dumps(dict(ns=ns, iterations=n, checksum=checksum)))
