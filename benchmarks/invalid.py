#!/usr/bin/env python3
"""Repeatable offline invalid-ZPL rejection probes with paired valid controls."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from accuracy.pixels import gray, sha
from formatting import NAMES, table

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SUITE = REPO / "test-data/invalid-zpl"
LANES = {
    "codyps-zpl": ["parse", "render"],
    "toolchain": ["parse"],
    "labelize": ["parse", "render"],
    "forge": ["parse", "render"],
    "go": ["parse", "render"],
    "ffi": ["render"],
    "binarykits": ["parse", "render"],
    "zplr": ["parse", "render"],
}
FAULTS = {"crash", "timeout", "process-error", "harness-error"}


def load_cases(directory=SUITE):
    manifest = json.loads((directory / "manifest.json").read_text())
    ids = set()
    for case in manifest["cases"]:
        if case["id"] in ids:
            raise ValueError("Duplicate case")
        ids.add(case["id"])
        for variant in ["control", "invalid"]:
            path = (directory / case[variant]["file"]).resolve()
            if (
                not path.is_relative_to(directory.resolve())
                or sha(path) != case[variant]["sha256"]
            ):
                raise ValueError(f"Invalid fixture: {path}")
    if not ids:
        raise ValueError("Empty corpus")
    return manifest


def attempt(command, env, source, output, mode, timeout):
    output.unlink(missing_ok=True)
    try:
        p = subprocess.run(
            command + ["probe-" + mode, str(source), "1", str(output), "400", "300"],
            env=env,
            capture_output=True,
            timeout=timeout,
        )
        stdout = p.stdout.decode(errors="replace")
        stderr = p.stderr.decode(errors="replace")
        result = dict(
            returncode=p.returncode, stdout=stdout[-2000:], diagnostic=stderr[-4000:]
        )
        if p.returncode:
            crash = (
                p.returncode < 0
                or "panicked at" in stderr
                or stderr.startswith("panic:")
            )
            result["status"] = "crash" if crash else "process-error"
        else:
            status = stdout.strip().splitlines()[-1] if stdout.strip() else ""
            if status not in {"accepted", "accepted-empty", "rejected"}:
                result.update(
                    status="harness-error",
                    diagnostic="Missing probe protocol verdict: " + stderr[-3000:],
                )
            else:
                result["status"] = status
                if status == "accepted" and mode == "render":
                    raster = gray(output)
                    result.update(
                        ink=int((raster < 128).sum()),
                        image_sha256=sha(output),
                        dimensions=[raster.shape[1], raster.shape[0]],
                    )
        return result
    except subprocess.TimeoutExpired as error:
        return dict(
            status="timeout",
            diagnostic=(error.stderr or b"").decode(errors="replace")[-4000:],
        )
    except (OSError, ValueError) as error:
        return dict(status="harness-error", diagnostic=str(error))
    finally:
        output.unlink(missing_ok=True)


def classify(controls, invalid, mode):
    all_rows = controls + invalid
    if any(r["status"] == "not_captured" for r in all_rows):
        return "not measured"
    if any(r["status"] in FAULTS for r in all_rows):
        return "execution failure"

    def signature(r):
        return (r["status"], r.get("ink"), r.get("image_sha256"))

    if (
        len({signature(r) for r in controls}) != 1
        or len({signature(r) for r in invalid}) != 1
    ):
        return "unstable"
    if controls[0]["status"] != "accepted" or (
        mode == "render" and not controls[0].get("ink")
    ):
        return "control failed"
    return "rejected" if invalid[0]["status"] == "rejected" else "accepted"


def render_report(data, dest):
    expected = {
        (c["id"], lib, mode)
        for c in data["cases"]
        for lib, modes in data["lanes"].items()
        for mode in modes
    }
    lookup = {(r["case"], r["library"], r["mode"]): r for r in data["results"]}
    if len(lookup) != len(data["results"]) or set(lookup) != expected:
        raise ValueError("Incomplete or duplicate result matrix")
    for row in lookup.values():
        if (
            len(row["control"]) != data["repeats"]
            or len(row["invalid"]) != data["repeats"]
        ):
            raise ValueError("Missing repetitions")
        if classify(row["control"], row["invalid"], row["mode"]) != row["outcome"]:
            raise ValueError("Stale verdict")
    manifest = {c["id"]: c for c in data["cases"]}
    text = [
        "# Invalid ZPL: rejection and recovery",
        "[Reproduce this run](../../../benchmarks/invalid/README.md) · [Exact fixtures](../../../test-data/invalid-zpl/manifest.json) · [Raw results and diagnostics](results.json)",
        f"Measured **{data['measured_utc']}** on `{data['host']}`. {len(data['cases'])} paired cases, {sum(map(len, data['lanes'].values()))} API lanes, {data['repeats']} repetitions per input: **{len(lookup) * 2 * data['repeats']} executions**.",
        "Each modified input is paired with a valid control using the same feature. **Rejected** means a returned library error, thrown exception, or error-severity diagnostic, with a successful control in every repeat. **Accepted** means no explicit error was reported; warnings may still appear. **Control failed** is inconclusive, including blank renderer controls. Panics, signals, timeouts, process/protocol failures and unstable outcomes never count as proper rejection.",
        "Parser lanes use the same default APIs as the benchmarks: codyps/zpl frames bytes; zpl-toolchain uses heuristic `parse_str` without specification tables or its separate validator. Renderer lanes run analysis and rendering. Error diagnostics may accompany a partial AST. These tests measure error signaling, not atomic refusal to produce any output or full standards validation. Builders (zpl-builder, Python ZPL, JSZPL) are N/A because they do not consume ZPL.",
        "The malformed group tests corrupt data; framing tests impose a complete-label contract that streaming APIs need not enforce. Fallback probes use invalid/out-of-range arguments for which ignoring, clamping or defaulting may be intentional. They are reported separately and do not contribute to malformed-data rejection counts. No case is sent to a printer.",
        "## Malformed-data results",
    ]
    summary = []
    for lib, modes in data["lanes"].items():
        for mode in modes:
            selected = [
                r
                for r in lookup.values()
                if r["library"] == lib
                and r["mode"] == mode
                and manifest[r["case"]]["group"] == "malformed"
            ]
            counts = Counter(r["outcome"] for r in selected)
            summary.append(
                [
                    NAMES[lib],
                    mode,
                    *[
                        counts[k]
                        for k in [
                            "rejected",
                            "accepted",
                            "control failed",
                            "execution failure",
                            "unstable",
                            "not measured",
                        ]
                    ],
                ]
            )
    text.append(
        table(
            [
                "Library",
                "API",
                "Rejected",
                "Accepted",
                "Control failed",
                "Execution failure",
                "Unstable",
                "Not measured",
            ],
            summary,
        )
    )
    for group in ["malformed", "framing", "fallback"]:
        text += [f"## {group.capitalize()} cases"]
        rows = []
        for case in data["cases"]:
            if case["group"] != group:
                continue
            for lib, modes in data["lanes"].items():
                for mode in modes:
                    row = lookup[case["id"], lib, mode]
                    rows.append(
                        [
                            f"[{case['id']}](#{case['id']})",
                            NAMES[lib],
                            mode,
                            row["outcome"],
                        ]
                    )
        text.append(table(["Case", "Library", "API", "Outcome"], rows))
    text += ["## Inputs and diagnostics"]
    for case in data["cases"]:
        text += [
            f"### {case['id']}",
            case["reason"] + " " + case["caveat"],
            f"Reference: {case['reference']}. [Valid control](../../../test-data/invalid-zpl/{case['control']['file']}) · [Modified input](../../../test-data/invalid-zpl/{case['invalid']['file']})",
        ]
        for lib, modes in data["lanes"].items():
            for mode in modes:
                row = lookup[case["id"], lib, mode]
                text += [f"**{NAMES[lib]} / {mode}: {row['outcome']}**"]
                diag = []
                for variant in ["control", "invalid"]:
                    for index, r in enumerate(row[variant], 1):
                        message = r.get("diagnostic", "").strip()
                        if message:
                            diag.append(
                                f"{variant}, repeat {index}, {r['status']}: {message}"
                            )
                if diag:
                    text += [
                        "~~~text\n" + "\n".join(diag).replace("~~~", "~ ~ ~") + "\n~~~"
                    ]
    return "\n\n".join(text).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--output", type=Path, default=REPO / "docs/benchmarks/invalid")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument(
        "--fail-on-crash",
        action="store_true",
        help="Fail after reporting library crashes or timeouts",
    )
    args = ap.parse_args()
    if args.repeats < 1 or args.timeout <= 0:
        ap.error("Positive repeats and timeout required")
    manifest = load_cases()
    dest = args.output
    if args.check or args.report_only:
        data = json.loads((dest / "results.json").read_text())
        if (
            data["manifest_sha256"] != sha(SUITE / "manifest.json")
            or data["cases"] != manifest["cases"]
        ):
            raise ValueError("Stale corpus")
        text = render_report(data, dest)
        if args.check:
            if (dest / "README.md").read_text() != text:
                raise ValueError("Stale report")
            print("Verified report and complete result matrix")
        else:
            (dest / "README.md").write_text(text)
        return
    cfg = json.loads((ROOT / "_work/config.json").read_text())
    selected = list(LANES) if args.only == "all" else args.only.split(",")
    if len(set(selected)) != len(selected) or any(
        n not in LANES or n not in cfg["commands"] for n in selected
    ):
        ap.error("Select built incoming-ZPL adapters")
    lanes = {n: LANES[n] for n in selected}
    dest.mkdir(parents=True, exist_ok=True)
    work = ROOT / "_work/invalid"
    work.mkdir(exist_ok=True)
    env = {**os.environ, **cfg["environment"]}
    rows = []
    for i, case in enumerate(manifest["cases"], 1):
        for lib, modes in lanes.items():
            for mode in modes:
                row = dict(case=case["id"], library=lib, mode=mode)
                for variant in ["control", "invalid"]:
                    row[variant] = [
                        attempt(
                            cfg["commands"][lib],
                            env,
                            SUITE / case[variant]["file"],
                            work / "probe.png",
                            mode,
                            args.timeout,
                        )
                        for _ in range(args.repeats)
                    ]
                row["outcome"] = classify(row["control"], row["invalid"], mode)
                rows.append(row)
        print(f"{i}/{len(manifest['cases'])} {case['id']}", flush=True)
    paths = [
        Path(__file__),
        ROOT / "adapters/rust/Cargo.lock",
        ROOT / "adapters/dotnet/packages.lock.json",
        ROOT / "adapters/node/package-lock.json",
        ROOT / "adapters/go/go.sum",
        ROOT / "sources.lock.json",
        ROOT / "requirements.txt",
        SUITE / "generate.py",
        ROOT / "adapters/rust/src/main.rs",
        ROOT / "adapters/rust/src/probe.rs",
        ROOT / "adapters/go/main.go",
        ROOT / "adapters/node/main.mjs",
        ROOT / "adapters/dotnet/Program.cs",
    ]
    # Record actual adapter executables and managed/native runtime dependencies.
    identities = {}
    for lib in lanes:
        files = [Path(x) for x in cfg["commands"][lib] if Path(x).is_file()]
        executable = shutil.which(cfg["commands"][lib][0], path=env.get("PATH"))
        if executable and Path(executable) not in files:
            files.append(Path(executable))
        if lib == "ffi":
            files.append(
                Path(cfg["commands"][lib][0]).parent
                / ("libzpl.dylib" if sys.platform == "darwin" else "libzpl.so")
            )
        if lib == "binarykits":
            files.extend((ROOT / "_work/dotnet-out").glob("*.dll"))
        identities[lib] = [dict(name=p.name, sha256=sha(p)) for p in files]
    data = dict(
        schema=1,
        suite=manifest["suite"],
        manifest_sha256=sha(SUITE / "manifest.json"),
        cases=manifest["cases"],
        lanes=lanes,
        repeats=args.repeats,
        timeout_seconds=args.timeout,
        measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        host=platform.platform(),
        python=platform.python_version(),
        adapters=identities,
        inputs={str(p.relative_to(REPO)): sha(p) for p in paths},
        results=rows,
    )
    (dest / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    (dest / "README.md").write_text(render_report(data, dest))
    attempts = [
        a for r in rows for variant in ("control", "invalid") for a in r[variant]
    ]
    if any(a["status"] in {"harness-error", "process-error"} for a in attempts) or any(
        r["outcome"] == "unstable" for r in rows
    ):
        raise SystemExit("Harness/process failure or instability; report preserved")
    crashes = sum(a["status"] in {"crash", "timeout"} for a in attempts)
    print(f"Recorded {len(attempts)} executions; {crashes} library crashes/timeouts")
    if args.fail_on_crash and crashes:
        raise SystemExit("Library crash/timeout; report preserved")


if __name__ == "__main__":
    main()
