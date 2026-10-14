"""Checks collections_probe.py on synthetic "reel embeddings": 1,000 items in 8 imbalanced
collections, the folder signal in a 16-dim subspace under noise in all 256 dims, and two
collections that overlap ("ai-video" and "ai-images"). The report must show the probe's
top-3 above its top-1, an ask-me rule that is more accurate on what it keeps, the overlapping
pair among the most confused, and per-collection numbers. Whether the probe beats kNN is
printed, not asserted: that is the question to answer on your real data.

    python test_collections_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collections_probe as cp  # noqa: E402


def main() -> int:
    rng = np.random.default_rng(3)
    names = ["ai-video", "ai-images", "techno", "rust", "agents", "design", "cooking", "misc"]
    sizes = [220, 180, 160, 120, 110, 90, 70, 50]
    centers = rng.normal(0, 1, (8, 16))
    centers[1] = centers[0] + rng.normal(0, 0.35, 16)  # ai-images sits next to ai-video
    X, y = [], []
    for c, (name, n) in enumerate(zip(names, sizes)):
        sig = centers[c] + rng.normal(0, 0.9, (n, 16))
        noise = rng.normal(0, 1.0, (n, 256))
        noise[:, :16] += sig * 1.6
        X.append(noise)
        y += [name] * n
    X = np.vstack(X)
    y = np.array(y, dtype=object)
    rep = cp.evaluate(X, y)
    a = rep["accuracy"]
    print({k: a[k] for k in ("knn_1", "knn_5", "knn_15", "probe", "probe_top3")}, rep["ask_me_rule"], rep["most_confused"][:2])
    problems = []
    if not a["probe_top3"] > a["probe"]:
        problems.append("top-3 should beat top-1")
    rule = rep["ask_me_rule"]
    if not (rule["accuracy_on_the_rest"] and rule["accuracy_on_the_rest"] > a["probe"] and 0 < rule["sent_to_you_pct"] < 100):
        problems.append(f"ask-me rule should send some to you and be more accurate on the rest: {rule}")
    if not any("ai-video -> ai-images" in m or "ai-images -> ai-video" in m for m in rep["most_confused"][:2]):
        problems.append(f"the overlapping pair should top the confusions: {rep['most_confused']}")
    if set(rep["per_collection"]) != set(names):
        problems.append("per-collection accuracy missing")
    top = cp.predict_top3(X, y, X[:2])
    if len(top) != 2 or len(top[0]) != 3:
        problems.append(f"predict_top3 shape: {top}")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
