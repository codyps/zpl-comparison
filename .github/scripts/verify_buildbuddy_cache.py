"""Prove remote cache reuse across fresh output bases, without a disk cache."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid


def verify(temporary):
    with tempfile.TemporaryDirectory(prefix="buildbuddy-probe-", dir=temporary) as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / ".bazelversion").write_text(
            (Path(__file__).resolve().parents[2] / ".bazelversion").read_text())
        (workspace / "MODULE.bazel").write_text('module(name="cache_probe")\n')
        # No language toolchains or project dependencies are needed for this action.
        (workspace / "probe.bzl").write_text(
            'def _impl(ctx):\n'
            '    out = ctx.actions.declare_file("result.txt")\n'
            '    ctx.actions.run_shell(outputs=[out], command="printf %s " + ctx.attr.value + " > " + out.path, mnemonic="CacheProbe")\n'
            '    return [DefaultInfo(files=depset([out]))]\n'
            'probe = rule(implementation=_impl, attrs={"value": attr.string()})\n'
        )
        value = uuid.uuid4().hex
        (workspace / "BUILD.bazel").write_text(
            'load(":probe.bzl", "probe")\nprobe(name="probe", value="' + value + '")\n'
        )
        for mode in ("upload", "download"):
            events = root / (mode + ".events.json")
            subprocess.run([
                "bazel", "--batch", "--output_base=" + str(root / mode),
                "build", "//:probe", "--disk_cache=", "--lockfile_mode=off",
                "--remote_accept_cached=" + ("false" if mode == "upload" else "true"),
                "--remote_upload_local_results=" + ("true" if mode == "upload" else "false"),
                "--build_event_json_file=" + str(events),
            ], cwd=workspace, check=True)
            if (workspace / "bazel-bin/result.txt").read_text() != value:
                raise RuntimeError("BuildBuddy cache probe returned incorrect contents")
            if mode == "download":
                metrics = next(json.loads(line)["buildMetrics"] for line in events.read_text().splitlines()
                               if "buildMetrics" in json.loads(line))
                runners = metrics["actionSummary"]["runnerCount"]
                if not any(r["name"] == "remote cache hit" and r["count"] > 0 for r in runners):
                    raise RuntimeError("Fresh output base did not reuse the BuildBuddy cache: " + str(runners))
        print("Verified BuildBuddy upload and remote cache hit with disk caching disabled.")


if __name__ == "__main__":
    verify(os.environ["RUNNER_TEMP"])
