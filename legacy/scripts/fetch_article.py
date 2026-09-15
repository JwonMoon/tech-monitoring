#!/usr/bin/env python3
"""Extract main article text from a blog post URL."""

import sys

import trafilatura


def get_article_text(url: str) -> str:
    html = trafilatura.fetch_url(url)
    if not html:
        raise RuntimeError(f"failed to fetch {url}")
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_images=True,
        output_format="markdown",
    )
    if not text:
        raise RuntimeError(f"failed to extract article body from {url}")
    return text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: fetch_article.py URL")
    print(get_article_text(sys.argv[1]))
