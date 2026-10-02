"""Measure built adapters serially at runtime, outside Bazel's action cache."""

import argparse
import json
import os
from pathlib import Path
import platform
import random
import statistics
import math
import time

from benchmarks.run import MODES, check_output, digest, measure

LIBRARIES = ("codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "zebrash", "zpl-renderer-js", "zebrash-ts")


def collect(libraries, fixtures, output, samples=5, seconds=0.2, memory_iterations=10, memory_launcher=None):
    memory_launcher = memory_launcher or Path(__file__).absolute().parents[1] / "memory_runner"
    if not memory_launcher.is_file():
        raise FileNotFoundError("Build the native memory_runner before collecting memory")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = output / "samples"
    artifacts.mkdir()
    deployments = {}
    for name in LIBRARIES:
        library = (libraries / ("library_" + name)).resolve(strict=True)
        command = json.loads((library / "command.json").read_text())
        deployments[name] = (library, [str(library / arg) if (library / arg).exists() else arg for arg in command])
    jobs = [(name, mode, fixture) for name in LIBRARIES for mode in MODES[name]
            for fixture in sorted(fixtures.glob("*.zpl"))]
    if not jobs:
        raise ValueError("No performance fixtures")
    random.Random(20260918).shuffle(jobs)
    rows = []
    for name, mode, fixture in jobs:
        library, command = deployments[name]
        env = {**os.environ, "ZPL_BENCH_MEMORY": "0", "DOTNET_ROOT": str(library / "runtime"),
               "LD_LIBRARY_PATH": str(library), "DYLD_LIBRARY_PATH": str(library),
               "ZPL_RENDER_PROFILE": "zd621-203dpi"}
        artifact = artifacts / f"{name}-{mode}-{fixture.stem}.{'png' if mode == 'png' else 'txt'}"
        row = dict(library=name, mode=mode, fixture=fixture.stem,
                   input_sha256=digest(fixture), input_bytes=fixture.stat().st_size,
                   measured_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        print(name, mode, fixture.stem, flush=True)
        try:
            invocation = command + [mode, str(fixture.resolve())]
            calibration = measure(invocation + ["1", str(artifact)], env, launcher=memory_launcher)
            check_output(artifact, mode, fixture.stem)
            iterations = max(1, min(1000000, round(seconds * 1e9 / calibration["ns"])))
            row["samples"] = [measure(invocation + [str(iterations), str(artifact)], env, launcher=memory_launcher) for _ in range(samples)]
            row["memory_samples"] = [measure(invocation + [str(memory_iterations), str(artifact)],
                                             {**env, "ZPL_BENCH_MEMORY": "1"}, launcher=memory_launcher)
                                     for _ in range(samples)]
            row["output_check"] = check_output(artifact, mode, fixture.stem)
            rss = [s["peak_rss_bytes"] for s in row["memory_samples"]]
            times = [s["ns"] / s["iterations"] for s in row["samples"]]
            row.update(status="ok", median_ns=statistics.median(times), min_ns=min(times),
                       max_ns=max(times), peak_rss_bytes=statistics.median(rss),
                       min_peak_rss_bytes=min(rss), max_peak_rss_bytes=max(rss))
        except RuntimeError as error:
            row.update(status="failed", error=str(error))
        rows.append(row)
    data = dict(schema=2,
                memory=dict(method="isolated-native-wait4", statistic="median", samples=samples,
                            iterations=memory_iterations, warmup_operations=3, output_operations=1), timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                host=dict(platform=platform.platform(), machine=platform.machine(), logical_cpus=os.cpu_count()),
                samples=samples, target_seconds=seconds, seed=20260918, sizes={name: json.loads((library / "size.json").read_text())
                       for name, (library, _) in deployments.items()}, results=rows,
                adapters={name: json.loads((library / "identity.json").read_text()) for name, (library, _) in deployments.items()},
                ci={key: os.environ.get(key) for key in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")})
    source_lock = fixtures.parent / "sources.lock.json"
    if source_lock.exists():
        data["sources"] = json.loads(source_lock.read_text())
    (output / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    # Preserve diagnostics but never publish a completely broken adapter as a successful run.
    missing = [name for name in LIBRARIES if not any(r["library"] == name and r["status"] == "ok" for r in rows)]
    if missing:
        raise RuntimeError("No successful measurements for: " + ", ".join(missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--seconds", type=float, default=0.2)
    parser.add_argument("--memory-iterations", type=int, default=10)
    parser.add_argument("--memory-launcher", type=Path)
    args = parser.parse_args()
    if args.samples < 1 or not math.isfinite(args.seconds) or args.seconds <= 0 or args.memory_iterations < 1:
        parser.error("samples, seconds and memory iterations must be positive")
    collect(args.libraries, args.fixtures, args.output.resolve(), args.samples, args.seconds, args.memory_iterations, args.memory_launcher)


if __name__ == "__main__":
    main()
