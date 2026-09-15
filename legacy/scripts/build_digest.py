#!/usr/bin/env python3
"""Assemble per-post summaries into a dated digest file and update the index."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIGESTS_DIR = ROOT / "digests"
INDEX_PATH = ROOT / "index.md"
SEEN_PATH = ROOT / "state" / "seen.json"

INDEX_MARKER = "<!-- digest-list -->"


def write_digest(date_str: str, summaries: list[dict]) -> pathlib.Path:
    """summaries: [{"title": ..., "url": ..., "summary": markdown}]"""
    DIGESTS_DIR.mkdir(exist_ok=True)
    path = DIGESTS_DIR / f"{date_str}.md"
    parts = [f"# NVIDIA 블로그 요약 — {date_str}\n"]
    if path.exists():
        # same-day rerun: append to existing digest
        parts = [path.read_text().rstrip() + "\n"]
    for item in summaries:
        parts.append(item["summary"].strip() + "\n\n---\n")
    path.write_text("\n".join(parts))
    return path


def update_index(date_str: str, count: int) -> None:
    text = INDEX_PATH.read_text()
    entry = f"- [{date_str}](digests/{date_str}.md) — {count}건"
    lines = text.splitlines()
    try:
        marker_idx = next(i for i, l in enumerate(lines) if l.strip() == INDEX_MARKER)
    except StopIteration:
        raise RuntimeError(f"index.md missing marker {INDEX_MARKER}")
    existing = f"- [{date_str}](digests/{date_str}.md)"
    lines = [l for l in lines if not l.startswith(existing)]
    marker_idx = next(i for i, l in enumerate(lines) if l.strip() == INDEX_MARKER)
    lines.insert(marker_idx + 1, entry)
    INDEX_PATH.write_text("\n".join(lines) + "\n")


def mark_seen(urls: list[str]) -> None:
    seen = json.loads(SEEN_PATH.read_text()) if SEEN_PATH.exists() else []
    seen_set = set(seen)
    for url in urls:
        if url not in seen_set:
            seen.append(url)
            seen_set.add(url)
    SEEN_PATH.write_text(json.dumps(seen, indent=2) + "\n")
