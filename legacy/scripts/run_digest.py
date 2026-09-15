#!/usr/bin/env python3
"""Orchestrator: fetch new posts, summarize each with Claude Code headless,
then build the daily digest."""

import datetime
import os
import pathlib
import subprocess
import sys
from zoneinfo import ZoneInfo

import build_digest
import fetch_article
import fetch_posts

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "summarize.md"
MAX_POSTS_PER_RUN = int(os.environ.get("DIGEST_MAX_POSTS", "20"))
CLAUDE_TIMEOUT_SEC = 600


def summarize(post: dict, body: str) -> str:
    prompt = (
        PROMPT_PATH.read_text()
        + f"제목: {post['title']}\n"
        + f"URL: {post['url']}\n"
        + f"게시일: {post['date']}\n"
        + f"카테고리: {', '.join(post['categories'])}\n\n"
        + "본문:\n\n"
        + body
    )
    last_err = None
    for _ in range(2):
        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "text", "--model", "sonnet"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT_SEC,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            last_err = (
                f"rc={result.returncode} "
                f"stderr={result.stderr.strip()[:500]!r} "
                f"stdout={result.stdout.strip()[:200]!r}"
            )
        except subprocess.TimeoutExpired:
            last_err = "timeout"
    raise RuntimeError(f"claude summarization failed: {last_err}")


def get_body(post: dict) -> str:
    # feed only carries a truncated excerpt, so always fetch the full article
    return fetch_article.get_article_text(post["url"])


def main() -> int:
    posts = fetch_posts.get_new_posts()[:MAX_POSTS_PER_RUN]
    if not posts:
        print("no new posts")
        return 0

    today = datetime.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    summaries = []
    done_urls = []
    failed = []
    for post in posts:
        print(f"processing: {post['title']}", flush=True)
        try:
            body = get_body(post)
            summary = summarize(post, body)
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr, flush=True)
            failed.append(post["url"])
            continue
        summaries.append({"title": post["title"], "url": post["url"], "summary": summary})
        done_urls.append(post["url"])

    if summaries:
        digest_path = build_digest.write_digest(today, summaries)
        total = digest_path.read_text().count("### [")
        build_digest.update_index(today, total)
        build_digest.mark_seen(done_urls)
        print(f"wrote {digest_path} ({len(summaries)} new, {len(failed)} failed)")

    # failed posts stay out of seen.json and retry on the next run
    return 0 if summaries or not posts else 1


if __name__ == "__main__":
    sys.exit(main())
