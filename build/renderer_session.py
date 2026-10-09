"""Bounded, sequential adapter processes used only for report rendering."""

import atexit
from collections import OrderedDict
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import tempfile
import time

# Each Bazel render worker owns its own pool. Periodic retirement bounds native
# allocator/Wasm heap growth without sharing application state between processes.
MAX_REQUESTS = 128
MAX_SESSIONS = 5
DYNAMIC_ENV = ("HOME", "TMPDIR", "DOTNET_CLI_HOME", "ZPL_RENDER_PROFILE", "ZPL_FONT_DIR")
_sessions = OrderedDict()


class Session:
    def __init__(self, command, env):
        self.directory = tempfile.TemporaryDirectory(prefix="zpl-session-", dir=os.environ.get("ZPL_BUILD_TMPDIR"))
        self.errors = open(Path(self.directory.name) / "stderr", "a+b")
        self.count = 0
        self.process = None
        try:
            environment = dict(env)
            for name in ("HOME", "TMPDIR", "DOTNET_CLI_HOME"):
                environment[name] = self.directory.name
            self.process = subprocess.Popen(
                command + ["--session"], cwd=self.directory.name, env=environment,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
                start_new_session=True,
            )
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.process is not None:
            # Kill the group even if its leader has exited, so timeouts cannot
            # leave descendants using request files after their cleanup.
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
        self.errors.close()
        self.directory.cleanup()

    def render(self, command, arguments, cwd, env, timeout):
        deadline = time.monotonic() + timeout
        self.count += 1
        request = dict(id=self.count, args=arguments, cwd=cwd,
                       env={name: env[name] for name in DYNAMIC_ENV})
        self.process.stdin.write((json.dumps(request) + "\n").encode())
        self.process.stdin.flush()
        response = bytearray()
        while b"\n" not in response:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise subprocess.TimeoutExpired(command, timeout)
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Renderer session exited without a response")
            response.extend(chunk)
            if len(response) > 65536:
                raise RuntimeError("Oversized renderer session response")
        result = json.loads(response)
        if result.get("id") != self.count or result.get("exitCode") != 0:
            raise RuntimeError("Renderer session failed; reproduce with the one-shot adapter")
        self.errors.seek(0, os.SEEK_END)
        length = self.errors.tell()
        self.errors.seek(max(0, length - 1800))
        diagnostic = self.errors.read() + result.get("diagnostic", "").encode()
        self.errors.seek(0)
        self.errors.truncate()
        return subprocess.CompletedProcess(command + arguments, 0, b"", diagnostic[-1800:])


def run(command, arguments, *, cwd, env, timeout, identity):
    deadline = time.monotonic() + timeout
    key = (tuple(command), identity, tuple(sorted((k, v) for k, v in env.items() if k not in DYNAMIC_ENV)))
    session = _sessions.pop(key, None)
    if session is not None and (session.count >= MAX_REQUESTS or session.process.poll() is not None):
        session.close()
        session = None
    if session is None:
        while len(_sessions) >= MAX_SESSIONS:
            _sessions.popitem(last=False)[1].close()
        session = Session(command, env)
    _sessions[key] = session
    try:
        return session.render(command, arguments, cwd, env, max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        _sessions.pop(key).close()
        raise
    except (OSError, ValueError, RuntimeError):
        _sessions.pop(key).close()
        # Preserve the existing return code and diagnostic for unsupported input,
        # crashes, and initialization errors. Never reuse a process after error.
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        with subprocess.Popen(command + arguments, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                              start_new_session=True) as process:
            try:
                stdout, stderr = process.communicate(timeout=remaining)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise
            return subprocess.CompletedProcess(command + arguments, process.returncode, stdout, stderr)


def close_all():
    while _sessions:
        _sessions.popitem()[1].close()


atexit.register(close_all)
