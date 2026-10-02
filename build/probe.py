"""One repeated valid/invalid probe pair against a pinned adapter deployment."""

import json
import os
from pathlib import Path
import tempfile
import time

from benchmarks.accuracy.pixels import sha
from benchmarks.invalid import attempt, classify


def probe(spec, destination):
    case, library, mode = spec["case"], spec["library"], spec["mode"]
    row = dict(case=case["id"], library=library, mode=mode,
               input_identity=spec["input_identity"],
               repeats=spec["repeats"], timeout_seconds=spec["timeout"],
               fixture_hashes={k: case[k]["sha256"] for k in ["control", "invalid"]})
    for variant, path in spec["sources"].items():
        if sha(Path(path)) != case[variant]["sha256"]:
            raise ValueError("Invalid probe input hash: " + path)
    if "baseline" in spec:
        saved = json.loads(Path(spec["baseline"]).read_text()) if spec["baseline"] else None
        if saved and all(saved.get(k) == row[k] for k in ["input_identity", "fixture_hashes", "repeats", "timeout_seconds"]):
            row = dict(saved, evidence_mode="saved")
        else:
            row.update(observed_utc="unavailable", evidence_mode="unavailable")
            for variant in ["control", "invalid"]:
                row[variant] = [dict(status="not_captured", diagnostic="No compatible trusted probe observation") for _ in range(spec["repeats"])]
    else:
        deployment = Path(spec["deployment"]).resolve()
        command = [str(deployment / p) if (deployment / p).exists() else p
                   for p in json.loads((deployment / "command.json").read_text())]
        row.update(observed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   adapter_identity_sha256=sha(deployment / "identity.json"))
        with tempfile.TemporaryDirectory(prefix="zpl-probe-") as temporary:
            env = {**os.environ, "HOME": temporary, "TMPDIR": temporary,
                   "DOTNET_CLI_HOME": temporary, "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                   "DOTNET_ROOT": str(deployment / "runtime"), "ZPL_RENDER_PROFILE": "zd621-203dpi",
                   "DYLD_LIBRARY_PATH": str(deployment),
                   "LD_LIBRARY_PATH": os.pathsep.join(filter(None, [str(deployment), os.environ.get("LD_LIBRARY_PATH", "")]))}
            for variant in ["control", "invalid"]:
                row[variant] = [attempt(command, env, Path(spec["sources"][variant]).resolve(),
                                         Path(temporary) / "probe.png", mode, spec["timeout"])
                                for _ in range(spec["repeats"])]
    row["outcome"] = classify(row["control"], row["invalid"], mode)
    Path(destination).write_text(json.dumps(row, sort_keys=True) + "\n")
    if row["outcome"] == "unstable" or any(r["status"] in {"harness-error", "process-error"}
                                          for variant in ["control", "invalid"] for r in row[variant]):
        raise ValueError("Probe harness/protocol failure or instability: " + json.dumps(row))
