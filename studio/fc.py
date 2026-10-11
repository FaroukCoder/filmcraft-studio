"""FilmCraft driver: one headless MCP session (`filmcraft-cli mcp`), commands in, JSON out.

A talking-head edit is 100+ commands; one CLI process per command reloads the project each
time, so the studio keeps a single MCP stdio session open instead (docs/agents.md §1)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

TICKS = 254_016_000_000  # FilmCraft time unit: ticks per second
CLI = Path(os.environ.get("FILMCRAFT_CLI", r"E:\AI\filmcraft\release-0.6.0\app"
                          r"\filmcraft-0.6.0-windows-x64-portable\filmcraft-cli.exe"))


def ticks(seconds: float) -> int:
    return round(seconds * TICKS)


class FilmCraftError(RuntimeError):
    pass


class Session:
    """`with Session() as fc: fc.run("file.newSequence", width=1080, ...)`"""

    def __init__(self, project: Path | None = None):
        args = [str(CLI), "mcp"] + (["--project", str(project)] if project and project.exists() else [])
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self._id = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "creative-studio", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def _send(self, msg: dict) -> None:
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method: str, params: dict) -> Any:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        while True:  # skip notifications (progress etc.) until our reply arrives
            line = self.proc.stdout.readline()
            if not line:
                raise FilmCraftError(f"FilmCraft MCP exited during {method}")
            msg = json.loads(line)
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise FilmCraftError(f"{method}: {msg['error']}")
                return msg["result"]

    def tool(self, name: str, **args: Any) -> Any:
        res = self._rpc("tools/call", {"name": name, "arguments": args})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise FilmCraftError(f"{name} {json.dumps(args)[:300]}: {text}")
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {"text": text}

    def run(self, command: str, **params: Any) -> Any:
        """Run one engine command (undoable)."""
        return self.tool("command_run", id=command, params=params)

    def batch(self, steps: list[tuple[str, dict]]) -> Any:
        return self.tool("command_batch", steps=[{"id": c, "params": p} for c, p in steps],
                         stop_on_error=True)

    def sequence(self) -> dict:
        return self.tool("sequence_inspect")
