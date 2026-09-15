"""발송 이력 (state/seen.json) — 같은 항목을 다음 날 다시 보내지 않기 위함."""
import json
from datetime import date, timedelta

from . import config

RETENTION_DAYS = 30


def load():
    try:
        data = json.loads(config.STATE_PATH.read_text(encoding="utf-8"))
        items = data.get("items", {})
        return items if isinstance(items, dict) else {}
    except (OSError, ValueError):
        return {}


def filter_unseen(articles, seen):
    if config.IGNORE_SEEN:
        return articles
    return [a for a in articles if a["uid"] not in seen]


def mark(seen, articles, today):
    for a in articles:
        for uid in a.get("member_uids") or [a["uid"]]:
            seen[uid] = today.isoformat()


def save(seen, today):
    cutoff = (today - timedelta(days=RETENTION_DAYS)).isoformat()
    kept = {k: v for k, v in seen.items() if v >= cutoff}
    config.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.STATE_PATH.write_text(
        json.dumps({"updated": today.isoformat(), "items": dict(sorted(kept.items()))},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    return len(kept)
