"""Link a tool named in a reel to its GitHub / Hugging Face repo, or say there is none.

Reel Brain's false matches come from taking the first search hit for a name. This does it
in three tiers:

1. **Explicit mentions** in the OCR text, caption and transcript (`github.com/owner/repo`,
   `huggingface.co/org/model`, `owner/repo` next to a word like "github" or "repo",
   `pip install x`, `npm i x`). Tech reels very often show the repo page on screen. Each
   one is checked to exist before it is trusted (an OCR typo is not a repo).
2. **Search candidates**, scored: the repo's name must equal the tool's name once both are
   normalised ("lang chain" = "LangChain" = "langchain"); then owner match, how many of the
   description's words the reel's own context covers, stars as a weak prior, and penalties
   for forks and archived repos. A substring is not a match ("Rez" is not "Rez Band").
3. **"no repo"** when nothing passes (many tools in reels are closed SaaS), and
   "ambiguous" when the top two are too close to call, so a person decides.

    python repo_linker.py "Karakeep" --context "self-hosted bookmark manager with AI tagging" --text ocr.txt

Uses GitHub's REST API (set GITHUB_TOKEN for search; unauthenticated search allows only a
few requests a minute) and the Hugging Face API. Pass a resolver of your own to test or to
use a cache.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

STOP = set("a an and are as at be but by for from has have i in into is it its of on or our so that the this to "
           "use used using was we with you your my me just very really here there what how why tool app new open "
           "source free best".split())
NOT_OWNERS = {"orgs", "topics", "features", "sponsors", "settings", "marketplace", "about", "login", "search",
              "collections", "trending", "explore", "pricing", "enterprise", "security", "apps", "users", "issues"}
CUE = re.compile(r"\b(github|git hub|repo|repository|clone|stars?|⭐|open[- ]source|hugging ?face|hf)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in STOP}


@dataclass
class Candidate:
    id: str  # "owner/name"
    kind: str = "github"  # github | hf-model | hf-dataset | hf-space | pypi | npm
    description: str = ""
    topics: list[str] = field(default_factory=list)
    stars: int = 0
    fork: bool = False
    archived: bool = False

    @property
    def owner(self) -> str:
        return self.id.split("/")[0] if "/" in self.id else ""

    @property
    def name(self) -> str:
        return self.id.split("/")[-1]


def explicit_mentions(text: str) -> list[tuple[str, str]]:
    """(kind, id) pairs written out in the text, in order of appearance, deduplicated."""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})", text, re.I):
        owner, repo = m.group(1), re.sub(r"(\.git)?[._-]*$", "", m.group(2))
        if owner.lower() not in NOT_OWNERS and repo:
            out.append(("github", f"{owner}/{repo}"))
    for m in re.finditer(r"huggingface\.co/(?:(datasets|spaces)/)?([A-Za-z0-9._-]{1,96})/([A-Za-z0-9._-]{1,96})", text, re.I):
        kind = {"datasets": "hf-dataset", "spaces": "hf-space"}.get((m.group(1) or "").lower(), "hf-model")
        out.append((kind, f"{m.group(2)}/{re.sub(r'[._-]*$', '', m.group(3))}"))
    # bare owner/repo: only near a cue word, both parts with a letter, not a URL path already taken
    for m in re.finditer(r"(?<![\w./:-])([A-Za-z][A-Za-z0-9-]{1,38})/([A-Za-z][A-Za-z0-9._-]{1,99})(?![\w/])", text):
        window = text[max(0, m.start() - 40): m.end() + 40]
        owner, repo = m.group(1), re.sub(r"[._-]*$", "", m.group(2))
        if CUE.search(window) and owner.lower() not in {"and", "w", "or", "km", "min", "n"} | NOT_OWNERS:
            pair = ("github", f"{owner}/{repo}")
            if not any(pair[1].lower() == o[1].lower() for o in out):
                out.append(pair)
    for m in re.finditer(r"\bpip3? install\s+(?:-U\s+)?([A-Za-z0-9][A-Za-z0-9._-]*)", text):
        out.append(("pypi", m.group(1)))
    for m in re.finditer(r"\bnpm (?:i|install)\s+(?:-g\s+)?(@?[A-Za-z0-9][A-Za-z0-9._/-]*)", text):
        out.append(("npm", m.group(1)))
    seen, uniq = set(), []
    for k, i in out:
        if (k, i.lower()) not in seen:
            seen.add((k, i.lower()))
            uniq.append((k, i))
    return uniq


def score(tool: str, context: str, c: Candidate) -> tuple[float, list[str]]:
    """0..1 and the reasons. Name equality is required; everything else orders the survivors."""
    t, n, o = norm(tool), norm(c.name), norm(c.owner)
    reasons = []
    if not t:
        return 0.0, ["empty tool name is a refusal, not a wildcard"]
    if n == t:
        name = 1.0
    elif n in {t + s for s in ("ai", "app", "js", "py", "cli", "hq", "dev", "io")} or t in {n + s for s in ("ai", "app")}:
        name = 0.8
        reasons.append(f"name {c.name!r} is {tool!r} plus a common suffix")
    else:
        return 0.0, [f"name {c.name!r} is not {tool!r}"]
    owner = 1.0 if o == t or (len(t) >= 3 and o.startswith(t)) or (len(o) >= 4 and t.startswith(o)) else 0.0
    if owner:
        reasons.append("owner matches the tool")
    desc = words(c.description + " " + " ".join(c.topics))
    ctx = words(context)
    fit = len(desc & ctx) / math.sqrt(max(len(desc), 1) * max(len(ctx), 1)) if desc and ctx else 0.0
    if desc & ctx:
        reasons.append(f"description shares {sorted(desc & ctx)[:6]} with the reel")
    stars = min(math.log10(c.stars + 1) / 5, 1.0)
    # The name only qualifies a candidate; what the reel says the tool does has to carry it.
    # Name + owner alone can't pass: that is how "Gamma" (slides SaaS) matched gamma-ray/gamma.
    s = 0.35 * name + 0.10 * owner + 0.45 * min(fit * 2, 1.0) + 0.10 * stars
    if c.fork:
        s -= 0.25
        reasons.append("fork")
    if c.archived:
        s -= 0.10
        reasons.append("archived")
    return round(max(s, 0.0), 3), reasons


class GitHubResolver:
    """Existence checks and search against GitHub's and Hugging Face's public APIs."""

    def __init__(self, token: str | None = None, timeout: float = 15.0):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout

    def _get(self, url: str, github: bool = True):
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "reel-brain"})
        if github and self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def get(self, kind: str, ident: str) -> Candidate | None:
        if kind == "github":
            d = self._get(f"https://api.github.com/repos/{ident}")
            if not d:
                return None
            return Candidate(d["full_name"], "github", d.get("description") or "", d.get("topics") or [],
                             int(d.get("stargazers_count", 0)), bool(d.get("fork")), bool(d.get("archived")))
        if kind.startswith("hf-"):
            path = {"hf-model": "models", "hf-dataset": "datasets", "hf-space": "spaces"}[kind]
            d = self._get(f"https://huggingface.co/api/{path}/{ident}", github=False)
            return Candidate(ident, kind, "", d.get("tags") or [], int(d.get("likes", 0))) if d else None
        return Candidate(ident, kind)  # package names: existence left to the package index

    def search(self, tool: str, limit: int = 10) -> list[Candidate]:
        q = urllib.parse.quote(f"{tool} in:name")
        d = self._get(f"https://api.github.com/search/repositories?q={q}&per_page={limit}") or {}
        return [Candidate(i["full_name"], "github", i.get("description") or "", i.get("topics") or [],
                          int(i.get("stargazers_count", 0)), bool(i.get("fork")), bool(i.get("archived")))
                for i in d.get("items", [])]


def link(tool: str, context: str, text: str, resolver, accept: float = 0.55, margin: float = 0.08) -> dict:
    """{status: explicit|matched|ambiguous|no_repo, best, candidates: [(id, score, reasons)]}."""
    for kind, ident in explicit_mentions(text):
        if kind in ("pypi", "npm"):
            continue
        c = resolver.get(kind, ident)
        if c and (kind != "github" or norm(c.name) == norm(tool) or not tool):
            return {"status": "explicit", "best": c.id, "kind": c.kind, "candidates": [(c.id, 1.0, ["written in the reel"])]}
    scored = sorted(((c.id, *score(tool, context, c)) for c in resolver.search(tool)), key=lambda x: -x[1])
    scored = [s for s in scored if s[1] > 0]
    if not scored or scored[0][1] < accept:
        return {"status": "no_repo", "best": None, "candidates": scored[:5]}
    if len(scored) > 1 and scored[0][1] - scored[1][1] < margin:
        return {"status": "ambiguous", "best": None, "candidates": scored[:5]}
    return {"status": "matched", "best": scored[0][0], "candidates": scored[:5]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tool")
    ap.add_argument("--context", default="", help="what the reel says the tool does")
    ap.add_argument("--text", help="file with OCR + caption + transcript")
    args = ap.parse_args(argv)
    text = open(args.text, encoding="utf-8").read() if args.text else ""
    print(json.dumps(link(args.tool, args.context, text, GitHubResolver()), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
