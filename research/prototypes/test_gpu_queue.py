"""Checks gpu_queue.py: transient failures are retried, a permanent one is parked without
blocking the rest, the queue waits while the DJ lock is set, and a hard crash in the middle
of an item (a worker process killed with os._exit) costs exactly that item on restart.

    python test_gpu_queue.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_queue as q  # noqa: E402


def main() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        con = q.connect(str(d / "a.db"))
        items = [f"reel{i}" for i in range(10)]
        if q.add(con, items) != 10 or q.add(con, items[:3]) != 0:
            problems.append("add should insert 10 then ignore duplicates")

        calls: list[str] = []
        seen_once: set[str] = set()

        def worker(item: str):
            calls.append(item)
            if item == "reel3" and item not in seen_once:
                seen_once.add(item)
                raise ConnectionRefusedError("llama-swap is swapping models")
            if item == "reel7":
                raise ValueError("vision model returned no JSON")
            return {"ok": item}

        t = [0.0]
        slept: list[float] = []
        polls = {"n": 0}

        def allowed():  # DJ app open for the first two polls
            polls["n"] += 1
            return polls["n"] > 2

        def sleep(s):
            slept.append(s)
            t[0] += s

        res = q.run(con, worker, max_attempts=3, backoff=10, wait_dj=30, sleep=sleep, clock=lambda: t[0], allowed=allowed)
        counts = res["counts"]
        if counts.get("done") != 9 or counts.get("failed") != 1:
            problems.append(f"expected 9 done / 1 failed, got {counts}")
        if slept[:2] != [30, 30]:
            problems.append(f"should wait twice for the DJ lock first: {slept[:4]}")
        if calls.count("reel3") != 2 or calls.count("reel7") != 3:
            problems.append(f"retries: reel3 x{calls.count('reel3')} (want 2), reel7 x{calls.count('reel7')} (want 3)")
        err = con.execute("SELECT error FROM jobs WHERE item='reel7'").fetchone()[0]
        if "no JSON" not in (err or ""):
            problems.append(f"failed item should keep its error: {err}")

        # hard crash mid-item, then restart
        db = d / "b.db"
        con2 = q.connect(str(db))
        q.add(con2, [f"r{i}" for i in range(6)])
        con2.close()
        log = d / "calls.txt"
        (d / "crashy.py").write_text(textwrap.dedent(f"""
            import os
            LOG = {str(log)!r}
            def process(item):
                with open(LOG, "a") as fh:
                    fh.write(item + "\\n")
                if item == "r3" and os.environ.get("CRASH") == "1":
                    os._exit(9)  # power cut / driver crash in the middle of r3
                return {{"ok": item}}
        """), encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=f"{d}{os.pathsep}{HERE}", GPU_DJ_LOCK=str(d / "none.lock"))
        cmd = [sys.executable, str(HERE / "gpu_queue.py"), "run", str(db), "--worker", "crashy:process"]
        first = subprocess.run(cmd, env={**env, "CRASH": "1"}, capture_output=True, text=True)
        second = subprocess.run(cmd, env=env, capture_output=True, text=True)
        lines = log.read_text().split()
        con3 = q.connect(str(db))
        st = q.status(con3)["counts"]
        if first.returncode == 0:
            problems.append("the first run should have died")
        if second.returncode != 0 or st.get("done") != 6:
            problems.append(f"restart should finish all 6: rc={second.returncode} {st} {second.stderr[-300:]}")
        if lines != ["r0", "r1", "r2", "r3", "r3", "r4", "r5"]:
            problems.append(f"only the in-flight item should run twice: {lines}")
        print({"run": {k: res[k] for k in ("done", "failed")}, "crash_calls": lines})
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
