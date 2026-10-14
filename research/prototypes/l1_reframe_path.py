"""Camera-operator-like 9:16 crop path from noisy subject positions (Top 10 #9).

Solves the L1-optimal camera path of Grundmann, Kwatra & Essa (CVPR 2011,
"Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths") for a
horizontal crop: minimise w1*|velocity| + w2*|acceleration| + w3*|jerk| (L1, so the
answer is made of holds, constant pans and short eases, like a person on a tripod)
plus a small pull toward the subject, subject to keeping the subject inside a safe
zone of the crop whenever it was detected. Missing detections (NaN) are free: the
camera holds or keeps panning through them.

Input positions can come from anything: rtmlib body keypoints, YuNet faces, a
SAM 2 track. Solve per shot (cut to cut), not across a cut.

    python l1_reframe_path.py centers.csv --frame-width 1920 --crop-width 608 > path.csv

centers.csv: one x per line (pixels), empty or 'nan' for "not found".
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from scipy import sparse
from scipy.optimize import linprog


def l1_path(x: np.ndarray, frame_w: float, crop_w: float, margin: float = 60.0,
            w1: float = 10.0, w2: float = 1.0, w3: float = 100.0, w0: float = 0.05) -> np.ndarray:
    """Crop-centre per frame. x: subject centre per frame (NaN = missing).

    Default weights follow the paper's 10 / 1 / 100 for the three derivatives;
    w0 is the pull toward the subject (small, so holds survive small sways)."""
    n = len(x)
    half = crop_w / 2.0
    lo_b, hi_b = half, frame_w - half
    if n < 4:
        known = x[~np.isnan(x)]
        c = float(np.clip(known.mean() if len(known) else frame_w / 2, lo_b, hi_b))
        return np.full(n, c)
    known = np.where(~np.isnan(x))[0]
    # variables: p (n), e1 (n-1), e2 (n-2), e3 (n-3), d (len(known))
    n1, n2, n3, nk = n - 1, n - 2, n - 3, len(known)
    nv = n + n1 + n2 + n3 + nk
    o1, o2, o3, od = n, n + n1, n + n1 + n2, n + n1 + n2 + n3
    c = np.zeros(nv)
    c[o1:o2], c[o2:o3], c[o3:od], c[od:] = w1, w2, w3, w0

    def diff_op(k: int) -> sparse.csr_matrix:
        d = sparse.identity(n, format="csr")
        for _ in range(k):
            d = (d[1:] - d[:-1])
        return d.tocsr()

    rows, b = [], []
    for k, off, m in ((1, o1, n1), (2, o2, n2), (3, o3, n3)):
        D = diff_op(k)
        E = sparse.csr_matrix((np.ones(m), (np.arange(m), off + np.arange(m))), shape=(m, nv))
        Dp = sparse.hstack([D, sparse.csr_matrix((m, nv - n))]).tocsr()
        rows += [Dp - E, -Dp - E]  # |D p| <= e
        b += [np.zeros(m), np.zeros(m)]
    if nk:
        P = sparse.csr_matrix((np.ones(nk), (np.arange(nk), known)), shape=(nk, nv))
        Ed = sparse.csr_matrix((np.ones(nk), (np.arange(nk), od + np.arange(nk))), shape=(nk, nv))
        rows += [P - Ed, -P - Ed]  # |p - x| <= d
        b += [x[known], -x[known]]
        safe = max(half - margin, 1.0)  # subject stays inside the safe zone
        rows += [P, -P]
        b += [x[known] + safe, -(x[known] - safe)]
    A = sparse.vstack(rows).tocsr()
    bounds = [(lo_b, hi_b)] * n + [(0, None)] * (nv - n)
    res = linprog(c, A_ub=A, b_ub=np.concatenate(b), bounds=bounds, method="highs")
    if res.status != 0:
        # Infeasible safe zone (subject wider than crop, or edge of frame): fall back to clamped subject.
        fill = np.interp(np.arange(n), known, x[known]) if nk else np.full(n, frame_w / 2)
        return np.clip(fill, lo_b, hi_b)
    return res.x[:n]


def describe(path: np.ndarray, eps: float = 0.05) -> dict:
    v = np.diff(path)
    return {
        "static_pct": round(100 * float(np.mean(np.abs(v) < eps)), 1),
        "max_speed_px_per_frame": round(float(np.max(np.abs(v))), 2),
        "direction_changes": int(np.sum(np.diff(np.sign(v[np.abs(v) >= eps])) != 0)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("centers")
    ap.add_argument("--frame-width", type=float, default=1920)
    ap.add_argument("--crop-width", type=float, default=608, help="1080 px tall source -> 608 px wide 9:16 crop")
    ap.add_argument("--margin", type=float, default=60)
    args = ap.parse_args(argv)
    vals = []
    for line in open(args.centers, encoding="utf-8"):
        line = line.strip()
        vals.append(float(line) if line and line.lower() != "nan" else np.nan)
    path = l1_path(np.array(vals), args.frame_width, args.crop_width, args.margin)
    for p in path:
        print(f"{p:.2f}")
    print(describe(path), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
