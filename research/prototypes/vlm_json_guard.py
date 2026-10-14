"""Get valid, bounded JSON out of a local vision model for one reel (Top 10 #3).

What it does, in the order the evidence suggests:
1. Downscales frames to <= 640 px on the long side and caps their number, then
   estimates prompt tokens (Qwen-VL: ~h*w/32^2 + 2 per image) and refuses to send a
   request that would overflow num_ctx (Ollama #13084: Qwen3-VL turns to garbage
   past num_ctx).
2. Uses Qwen's recommended Instruct sampling (temperature 0.7, top-p 0.8, top-k 20,
   presence penalty 1.5), not greedy decoding, which loops more (Qwen3-VL #1611).
3. Asks for a schema with hard bounds (maxItems, maxLength, enums) so the output
   cannot grow forever, caps output tokens, and rejects text that repeats itself.
4. Validates with Pydantic; on failure retries with half the frames, then falls back
   to two passes: free-text notes, then a text-only call that only formats JSON.

Works against Ollama's native API (--api ollama) or any OpenAI-compatible server
such as llama-server or llama-swap (--api openai).

    python vlm_json_guard.py reel.mp4 --api ollama --model qwen3-vl:8b
    python vlm_json_guard.py reel.mp4 --api openai --url http://127.0.0.1:8080 --model qwen3-vl-8b
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
from enum import Enum
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError


class ToolKind(str, Enum):
    open_source = "open_source"
    saas = "saas"
    model = "model"
    library = "library"
    unknown = "unknown"


class Tool(BaseModel):
    name: str = Field(max_length=60)
    kind: ToolKind
    # Exactly what is visible on screen or said aloud; never a guess.
    url_or_repo_seen: str | None = Field(default=None, max_length=200)


class ReelNote(BaseModel):
    summary: str = Field(max_length=400)
    takeaways: list[str] = Field(max_length=5)
    tools: list[Tool] = Field(max_length=8)
    topics: list[str] = Field(max_length=5)
    language: Literal["en", "ar", "mixed", "other"]


def bounded_schema() -> dict:
    """Pydantic's schema plus per-item string bounds (maxItems comes from max_length)."""
    schema = ReelNote.model_json_schema()
    props = schema["properties"]
    props["takeaways"]["items"]["maxLength"] = 160
    props["topics"]["items"]["maxLength"] = 40
    return schema


QWEN_VL_INSTRUCT_SAMPLING = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "presence_penalty": 1.5}

PROMPT = (
    "You are cataloguing a saved short video. The frames are in time order; the transcript and "
    "on-screen text follow. Return JSON only, matching the schema. Use at most 5 takeaways, "
    "8 tools and 5 topics. For each tool, copy a URL or owner/repo only if it is visible or "
    "spoken; otherwise null. Do not repeat items."
)


def extract_frames(video: Path, n: int, long_side: int = 640) -> list[tuple[bytes, int, int]]:
    """n evenly spaced JPEG frames, scaled so the long side is <= long_side."""
    dur = float(json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout)["format"]["duration"])
    scale = f"scale='if(gt(iw,ih),min({long_side},iw),-2)':'if(gt(iw,ih),-2,min({long_side},ih))'"
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            t = dur * (i + 0.5) / n
            out = Path(tmp) / f"f{i}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                            "-frames:v", "1", "-vf", scale, "-q:v", "4", str(out)], check=True)
            w, h = _jpeg_size(out)
            frames.append((out.read_bytes(), w, h))
    return frames


def _jpeg_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    st = json.loads(out.stdout)["streams"][0]
    return int(st["width"]), int(st["height"])


def estimate_tokens(frames: list[tuple[bytes, int, int]], text: str) -> int:
    image_tokens = sum(w * h // (32 * 32) + 2 for _, w, h in frames)
    return image_tokens + len(text) // 3 + 64


def looks_looping(text: str, min_len: int = 24, max_repeats: int = 4) -> bool:
    """True if some chunk of >= min_len characters repeats max_repeats+ times."""
    return re.search(r"(.{%d,}?)\1{%d,}" % (min_len, max_repeats - 1), text, re.S) is not None


def _call(args, frames, text: str, schema: dict | None, max_tokens: int) -> str:
    images = [base64.b64encode(b).decode() for b, _, _ in frames]
    if args.api == "ollama":
        body = {
            "model": args.model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": text, "images": images}],
            "options": {**QWEN_VL_INSTRUCT_SAMPLING, "num_ctx": args.num_ctx, "num_predict": max_tokens},
        }
        if schema:
            body["format"] = schema
        r = httpx.post(f"{args.url}/api/chat", json=body, timeout=args.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]
    content = [{"type": "text", "text": text}] + [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}} for b in images]
    body = {"model": args.model, "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens, **QWEN_VL_INSTRUCT_SAMPLING}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reel_note", "schema": schema}}
    r = httpx.post(f"{args.url}/v1/chat/completions", json=body, timeout=args.timeout)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def note_for(video: Path | None, context: str, args, frames=None) -> tuple[ReelNote | None, list[dict]]:
    """Returns (note or None, attempt log)."""
    frames = frames if frames is not None else extract_frames(video, args.frames)
    schema = bounded_schema()
    text = PROMPT + "\n\n" + context[: args.max_context_chars]
    log: list[dict] = []
    plans = [("full", frames), ("half_frames", frames[: max(1, len(frames) // 2)])]
    for name, fr in plans:
        tokens = estimate_tokens(fr, text)
        if tokens + args.max_tokens > args.num_ctx:
            log.append({"attempt": name, "skipped": f"needs ~{tokens} prompt tokens, num_ctx {args.num_ctx}"})
            continue
        try:
            raw = _call(args, fr, text, schema, args.max_tokens)
        except httpx.HTTPError as e:
            log.append({"attempt": name, "error": str(e)})
            continue
        if looks_looping(raw):
            log.append({"attempt": name, "error": "repetition detected", "prompt_tokens": tokens})
            continue
        try:
            note = ReelNote.model_validate_json(raw)
            log.append({"attempt": name, "ok": True, "prompt_tokens": tokens})
            return note, log
        except ValidationError as e:
            log.append({"attempt": name, "error": f"invalid: {e.error_count()} errors", "prompt_tokens": tokens})
    # Two-pass fallback: describe freely (no schema, short), then format text-only.
    try:
        fr = frames[: max(1, len(frames) // 2)]
        notes = _call(args, fr, text.replace("Return JSON only, matching the schema.",
                                             "Write short plain-text notes."), None, 400)
        if not looks_looping(notes):
            raw = _call(args, [], "Turn these notes into JSON matching the schema. Notes:\n" + notes, schema, args.max_tokens)
            note = ReelNote.model_validate_json(raw)
            log.append({"attempt": "two_pass", "ok": True})
            return note, log
        log.append({"attempt": "two_pass", "error": "repetition in notes"})
    except (httpx.HTTPError, ValidationError) as e:
        log.append({"attempt": "two_pass", "error": str(e)[:200]})
    return None, log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--context", default="", help="transcript + caption + OCR text")
    ap.add_argument("--api", choices=["ollama", "openai"], default="ollama")
    ap.add_argument("--url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen3-vl:8b")
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--max-context-chars", type=int, default=6000)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args(argv)
    note, log = note_for(args.video, args.context, args)
    print(json.dumps({"note": note.model_dump(mode="json") if note else None, "attempts": log}, indent=2, ensure_ascii=False))
    return 0 if note else 2


if __name__ == "__main__":
    sys.exit(main())
