"""발송 이력 (state/seen_<주제 slug>.json) — 같은 항목을 다음 날 다시 보내지 않기 위함."""
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


# ─── GitHub 조직 저장소 스냅샷 (state/github_<slug>.json) ──────────────────────
# 어제 조직에 있던 저장소 목록·스타 수. "스냅샷에 없던 저장소" = 새로 공개된 저장소.
# created_at 은 비공개 시절 날짜라 공개 시점을 알려주지 않으므로 스냅샷 비교가 유일하게 믿을 만하다.
GITHUB_RETENTION_DAYS = 90
_github = None


def github_load():
    """{"repos": {"org/name": {"stars": int, "created": "YYYY-MM-DD", "seen": "YYYY-MM-DD"}}} (캐시)."""
    global _github
    if _github is None:
        try:
            data = json.loads(config.GITHUB_STATE_PATH.read_text(encoding="utf-8"))
            repos = data.get("repos", {})
            _github = {"repos": repos if isinstance(repos, dict) else {}}
        except (OSError, ValueError):
            _github = {"repos": {}}
    return _github


def github_save(today):
    snap = github_load()
    cutoff = (today - timedelta(days=GITHUB_RETENTION_DAYS)).isoformat()
    kept = {k: v for k, v in snap["repos"].items() if (v.get("seen") or "") >= cutoff}
    config.GITHUB_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.GITHUB_STATE_PATH.write_text(
        json.dumps({"updated": today.isoformat(), "repos": dict(sorted(kept.items()))},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    return len(kept)
