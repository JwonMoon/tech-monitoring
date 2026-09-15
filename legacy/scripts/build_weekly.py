#!/usr/bin/env python3
"""Build a weekly highlights page from the past week's daily digests."""

import datetime
import pathlib
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIGESTS_DIR = ROOT / "digests"
WEEKLY_DIR = ROOT / "weekly"
INDEX_PATH = ROOT / "index.md"
PROMPT_PATH = ROOT / "prompts" / "weekly.md"

DIGEST_MARKER = "<!-- digest-list -->"
WEEKLY_MARKER = "<!-- weekly-list -->"
CLAUDE_TIMEOUT_SEC = 600


def collect_week_digests(today: datetime.date) -> tuple[str, list[str]]:
    start = today - datetime.timedelta(days=7)
    parts, dates = [], []
    for path in sorted(DIGESTS_DIR.glob("*.md")):
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.md", path.name)
        if not m:
            continue
        d = datetime.date.fromisoformat(m.group(1))
        if start <= d < today:
            parts.append(path.read_text())
            dates.append(m.group(1))
    return "\n\n".join(parts), dates


def summarize_week(digest_text: str) -> str:
    prompt = PROMPT_PATH.read_text() + digest_text
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
                f"stderr={result.stderr.strip()[:500]!r}"
            )
        except subprocess.TimeoutExpired:
            last_err = "timeout"
    raise RuntimeError(f"weekly summarization failed: {last_err}")


def update_index(week_file: str, label: str) -> None:
    text = INDEX_PATH.read_text()
    if WEEKLY_MARKER not in text:
        text = text.replace(
            "## 날짜별 다이제스트",
            f"## 주간 하이라이트\n\n{WEEKLY_MARKER}\n\n## 날짜별 다이제스트",
        )
    lines = text.splitlines()
    marker_idx = next(i for i, l in enumerate(lines) if l.strip() == WEEKLY_MARKER)
    entry = f"- [{label}](weekly/{week_file})"
    if entry not in lines:
        lines.insert(marker_idx + 1, entry)
    INDEX_PATH.write_text("\n".join(lines) + "\n")


def main() -> int:
    today = datetime.datetime.now(ZoneInfo("Asia/Seoul")).date()
    digest_text, dates = collect_week_digests(today)
    if not dates:
        print("no digests in the past week")
        return 0

    highlights = summarize_week(digest_text)
    label = f"{dates[0]} ~ {dates[-1]}"
    WEEKLY_DIR.mkdir(exist_ok=True)
    week_file = f"{today.isoformat()}.md"
    (WEEKLY_DIR / week_file).write_text(
        f"# 주간 하이라이트 — {label}\n\n{highlights}\n"
    )
    update_index(week_file, label)
    print(f"wrote weekly/{week_file} (from {len(dates)} digests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
