"""Is kNN the right way to file reels into collections? Measure it on your own embeddings.

Reel Brain files reels by kNN over EmbeddingGemma vectors (63 % against your own folders).
This compares, with the same 5-fold cross-validation and the same vectors:
kNN (k = 1, 5, 15, cosine), a logistic-regression "linear probe", and the probe's top-3
(what a one-click "pick one of three" UI would get right), plus a confidence rule that sends
low-margin reels to you instead of guessing, with how many it would send and how accurate
the rest are. Per-collection accuracy and the most-confused pairs say which folders overlap.

    python collections_probe.py embeddings.npy labels.txt
    python collections_probe.py embeddings.npy labels.txt --predict new.npy   # top-3 for new reels

embeddings.npy: one row per reel (any dimension). labels.txt: one collection name per line,
same order.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import normalize


def _probe() -> LogisticRegression:
    return LogisticRegression(max_iter=3000, C=2.0, class_weight="balanced")


def evaluate(X: np.ndarray, y: np.ndarray, folds: int = 5, margin: float = 0.15, seed: int = 0) -> dict:
    X = normalize(X)
    counts = Counter(y)
    folds = max(2, min(folds, min(counts.values())))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    classes = np.array(sorted(counts))
    pred = {f"knn_{k}": np.empty(len(y), dtype=object) for k in (1, 5, 15)}
    probe_pred = np.empty(len(y), dtype=object)
    top3_hit = np.zeros(len(y), bool)
    margins = np.zeros(len(y))
    for tr, te in cv.split(X, y):
        for k in (1, 5, 15):
            m = KNeighborsClassifier(n_neighbors=min(k, len(tr)), metric="cosine", weights="distance").fit(X[tr], y[tr])
            pred[f"knn_{k}"][te] = m.predict(X[te])
        clf = _probe().fit(X[tr], y[tr])
        proba = clf.predict_proba(X[te])
        order = np.argsort(-proba, axis=1)
        cl = clf.classes_
        probe_pred[te] = cl[order[:, 0]]
        top3_hit[te] = [y[i] in set(cl[order[j, :3]]) for j, i in enumerate(te)]
        margins[te] = proba[np.arange(len(te)), order[:, 0]] - proba[np.arange(len(te)), order[:, 1]]
    acc = {name: round(float(np.mean(p == y)), 3) for name, p in pred.items()}
    acc["probe"] = round(float(np.mean(probe_pred == y)), 3)
    acc["probe_top3"] = round(float(top3_hit.mean()), 3)
    sure = margins >= margin
    per = {c: round(float(np.mean(probe_pred[y == c] == c)), 3) for c in classes}
    conf = Counter((a, b) for a, b in zip(y, probe_pred) if a != b).most_common(6)
    return {
        "n": int(len(y)), "collections": int(len(classes)), "folds": folds,
        "accuracy": acc,
        "ask_me_rule": {"margin": margin, "sent_to_you_pct": round(100 * float(1 - sure.mean()), 1),
                        "accuracy_on_the_rest": round(float(np.mean(probe_pred[sure] == y[sure])), 3) if sure.any() else None},
        "per_collection": per,
        "most_confused": [f"{a} -> {b}: {n}" for (a, b), n in conf],
        "majority_baseline": round(counts.most_common(1)[0][1] / len(y), 3),
    }


def predict_top3(X: np.ndarray, y: np.ndarray, Xnew: np.ndarray) -> list[list[tuple[str, float]]]:
    clf = _probe().fit(normalize(X), y)
    proba = clf.predict_proba(normalize(Xnew))
    return [[(str(clf.classes_[j]), round(float(p[j]), 3)) for j in np.argsort(-p)[:3]] for p in proba]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("embeddings")
    ap.add_argument("labels")
    ap.add_argument("--predict")
    ap.add_argument("--margin", type=float, default=0.15)
    args = ap.parse_args(argv)
    X = np.load(args.embeddings)
    y = np.array([line.strip() for line in open(args.labels, encoding="utf-8") if line.strip()], dtype=object)
    if len(X) != len(y):
        print(f"{len(X)} embeddings but {len(y)} labels", file=sys.stderr)
        return 2
    if args.predict:
        print(json.dumps(predict_top3(X, y, np.load(args.predict)), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(evaluate(X, y, margin=args.margin), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
