"""Bazel JSON worker protocol; each request remains an independent cached action."""

import contextlib
import importlib
import io
import json
import shutil
import sys
import traceback
from pathlib import Path


def execute(kind, arguments):
    module = importlib.import_module("build." + kind)
    function = getattr(
        module,
        {
            "render": "render",
            "compare": "comparison",
            "pages": "write",
            "aggregate": "aggregate",
            "preview": "main",
            "relation": "main",
        }[kind],
    )
    spec = json.loads(Path(arguments[0]).read_text())
    for filename in arguments[1:]:
        path = Path(filename)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
    function(spec, *arguments[1:])


def main():
    kind = sys.argv[1]
    if "--persistent_worker" not in sys.argv:
        arguments = sys.argv[2:]
        if len(arguments) == 1 and arguments[0].startswith("@"):
            arguments = Path(arguments[0][1:]).read_text().splitlines()
        execute(kind, arguments)
        return
    for line in sys.stdin:
        request = json.loads(line)
        diagnostics = io.StringIO()
        status = 0
        with (
            contextlib.redirect_stdout(diagnostics),
            contextlib.redirect_stderr(diagnostics),
        ):
            try:
                execute(kind, request["arguments"])
            except Exception:  # noqa: BLE001 - protocol errors must not kill subsequent requests
                traceback.print_exc()
                status = 1
        print(
            json.dumps(
                {
                    "requestId": request.get("requestId", 0),
                    "exitCode": status,
                    "output": diagnostics.getvalue(),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
