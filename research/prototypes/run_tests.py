"""Run every prototype test and print a one-line summary for each."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    failed = 0
    for test in sorted(HERE.glob("test_*.py")):
        t0 = time.time()
        res = subprocess.run([sys.executable, str(test)], capture_output=True, text=True, cwd=HERE)
        last = (res.stdout.strip().splitlines() or ["(no output)"])[-1]
        ok = res.returncode == 0 and last.startswith("PASS")
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {test.name:38s} {time.time() - t0:5.1f}s")
        if not ok:
            print(res.stdout[-1500:], res.stderr[-1500:], sep="\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
