"""Checks laya_eval.py on synthetic routes: a router that is right ~40 % of the time
but reports ~0.9 confidence (what Laya's README says about base checkpoints), and
messages whose words make the right route learnable.

    python test_laya_eval.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import laya_eval  # noqa: E402

ROUTES = {
    "coding": ["fix the bug in", "refactor", "write a python script", "why does cargo fail", "unit test for"],
    "vault": ["add a note about", "what did I write on", "summarise my notes on", "link this to", "obsidian page"],
    "media": ["cut a reel from", "render the clip", "beat grid for", "make a 9:16 version", "captions for"],
    "chat": ["how are you", "thanks", "good morning", "what do you think about", "tell me a joke"],
}
TOPICS = ["the set", "whatstheid", "hermes", "techno", "my vault", "filmcraft", "the drop", "laya", "ذلك", "الحفلة"]


def main() -> int:
    rng = np.random.default_rng(0)
    rows = []
    labels = list(ROUTES)
    for i in range(400):
        lab = labels[i % 4]
        text = f"{rng.choice(ROUTES[lab])} {rng.choice(TOPICS)}"
        laya = lab if rng.random() < 0.4 else rng.choice([l for l in labels if l != lab])
        rows.append({"text": text, "laya": laya, "confidence": float(np.clip(rng.normal(0.9, 0.05), 0, 1)), "label": lab})
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rep = laya_eval.report(laya_eval.load(f.name))
    print(json.dumps({k: rep[k] for k in ("accuracy", "majority_class_baseline", "ece", "baseline_cv_accuracy")}))
    problems = []
    if not 0.33 < rep["accuracy"] < 0.47:
        problems.append(f"accuracy {rep['accuracy']}")
    if rep["ece"] < 0.35:
        problems.append(f"ECE should expose over-confidence, got {rep['ece']}")
    if rep.get("baseline_cv_accuracy", 0) < 0.9:
        problems.append(f"baseline should learn the routes, got {rep.get('baseline_cv_accuracy')}")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
