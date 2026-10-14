"""A crash-safe job queue for long GPU batches (shared by Reel Brain, Creative Studio renders,
whatstheID analysis).

Your PC has crashed on long GPU runs, and a crash used to cost the whole run. This keeps
one row per item in SQLite (WAL mode, so a power cut doesn't corrupt it) and works through
them one at a time:

- an item is marked done the moment it finishes, so a crash or reboot costs one item;
- items left "running" by a crash go back to "queued" on the next start;
- before each item it asks `dj_guard.gpu_allowed()`, and waits while Serato or Ableton runs;
- a failure is retried with backoff (connection refused while llama-swap swaps models is
  normal), and after `max_attempts` the item is parked as "failed" with its error, so one
  bad reel doesn't block the other 999;
- `status()` gives counts for a Telegram/Hermes report; Hermes cron's no-agent mode can run
  `python gpu_queue.py run reels.db` every night.

    python gpu_queue.py add reels.db reel_urls.txt
    python gpu_queue.py run reels.db --worker my_reel_brain:process
    python gpu_queue.py status reels.db

The worker is any function `process(item: str) -> dict | None`; whatever it returns is
stored as the item's result (JSON).
"""
from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dj_guard  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  item TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'queued',   -- queued | running | done | failed
  attempts INTEGER NOT NULL DEFAULT 0,
  next_try REAL NOT NULL DEFAULT 0,
  result TEXT, error TEXT, updated REAL
);
"""


def connect(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(db, timeout=30, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.executescript(SCHEMA)
    return con


def add(con: sqlite3.Connection, items: list[str]) -> int:
    before = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    con.executemany("INSERT OR IGNORE INTO jobs(item, updated) VALUES (?, ?)", [(i, time.time()) for i in items if i.strip()])
    return con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] - before


def recover(con: sqlite3.Connection) -> int:
    """Items a crash left 'running' go back to the queue."""
    return con.execute("UPDATE jobs SET status='queued' WHERE status='running'").rowcount


def status(con: sqlite3.Connection) -> dict:
    rows = dict(con.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    failed = [r[0] for r in con.execute("SELECT item FROM jobs WHERE status='failed' LIMIT 5")]
    return {"counts": rows, "failed_examples": failed}


def _next(con: sqlite3.Connection, now: float):
    return con.execute("SELECT item, attempts FROM jobs WHERE status='queued' AND next_try <= ? "
                       "ORDER BY attempts, rowid LIMIT 1", (now,)).fetchone()


def run(con: sqlite3.Connection, worker, max_attempts: int = 3, backoff: float = 30.0, wait_dj: float = 30.0,
        max_items: int | None = None, sleep=time.sleep, clock=time.time, allowed=dj_guard.gpu_allowed) -> dict:
    recover(con)
    done = failed = 0
    while max_items is None or done + failed < max_items:
        if not allowed():
            sleep(wait_dj)  # Serato/Ableton is open: wait, don't fight the set
            continue
        row = _next(con, clock())
        if row is None:
            pending = con.execute("SELECT MIN(next_try) FROM jobs WHERE status='queued'").fetchone()[0]
            if pending is None:
                break
            sleep(max(0.0, min(pending - clock(), backoff)))
            continue
        item, attempts = row
        con.execute("UPDATE jobs SET status='running', updated=? WHERE item=?", (clock(), item))
        try:
            result = worker(item)
            con.execute("UPDATE jobs SET status='done', result=?, error=NULL, updated=? WHERE item=?",
                        (json.dumps(result, ensure_ascii=False) if result is not None else None, clock(), item))
            done += 1
        except Exception as e:  # noqa: BLE001 - one bad item must not stop the batch
            attempts += 1
            err = f"{type(e).__name__}: {e}"[:500]
            if attempts >= max_attempts:
                con.execute("UPDATE jobs SET status='failed', attempts=?, error=?, updated=? WHERE item=?",
                            (attempts, err, clock(), item))
                failed += 1
            else:
                con.execute("UPDATE jobs SET status='queued', attempts=?, error=?, next_try=?, updated=? WHERE item=?",
                            (attempts, err, clock() + backoff * 2 ** (attempts - 1), clock(), item))
    return {"done": done, "failed": failed, **status(con)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("db")
    a.add_argument("items", help="text file, one item (URL, path) per line")
    r = sub.add_parser("run")
    r.add_argument("db")
    r.add_argument("--worker", required=True, help="module:function, e.g. my_reel_brain:process")
    r.add_argument("--max-attempts", type=int, default=3)
    r.add_argument("--backoff", type=float, default=30.0)
    r.add_argument("--max-items", type=int)
    s = sub.add_parser("status")
    s.add_argument("db")
    args = ap.parse_args(argv)
    con = connect(args.db)
    if args.cmd == "add":
        print(f"added {add(con, Path(args.items).read_text(encoding='utf-8').splitlines())}")
    elif args.cmd == "status":
        print(json.dumps(status(con), indent=2))
    else:
        mod, fn = args.worker.split(":")
        worker = getattr(importlib.import_module(mod), fn)
        try:
            print(json.dumps(run(con, worker, args.max_attempts, args.backoff, max_items=args.max_items), indent=2))
        except KeyboardInterrupt:
            traceback.print_exc(limit=0)
            print(json.dumps(status(con), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
