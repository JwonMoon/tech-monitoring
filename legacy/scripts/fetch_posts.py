#!/usr/bin/env python3
"""Fetch new posts from the NVIDIA developer blog RSS feed."""

import json
import os
import pathlib
import sys

import feedparser

FEED_URL = "https://developer.nvidia.com/blog/feed"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
ROOT = pathlib.Path(__file__).resolve().parent.parent
SEEN_PATH = ROOT / "state" / "seen.json"

# comma-separated substring match against post categories; empty = all posts
CATEGORY_FILTER = [
    c.strip().lower()
    for c in os.environ.get("DIGEST_CATEGORIES", "").split(",")
    if c.strip()
]


def matches_filter(categories: list[str]) -> bool:
    if not CATEGORY_FILTER:
        return True
    return any(f in cat.lower() for cat in categories for f in CATEGORY_FILTER)


def load_seen() -> set[str]:
    if SEEN_PATH.exists():
        return set(json.loads(SEEN_PATH.read_text()))
    return set()


def get_new_posts() -> list[dict]:
    feed = feedparser.parse(FEED_URL, agent=USER_AGENT)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"feed parse failed: {feed.get('bozo_exception')}")

    seen = load_seen()
    posts = []
    for entry in feed.entries:
        url = entry.get("link", "")
        if not url or url in seen:
            continue
        categories = [t["term"] for t in entry.get("tags", [])]
        if not matches_filter(categories):
            continue
        content = ""
        if entry.get("content"):
            content = entry["content"][0].get("value", "")
        posts.append(
            {
                "title": entry.get("title", "(untitled)"),
                "url": url,
                "date": entry.get("published", ""),
                "categories": categories,
                "feed_content": content,
                "description": entry.get("summary", ""),
            }
        )
    return posts


if __name__ == "__main__":
    json.dump(get_new_posts(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
