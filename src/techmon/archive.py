"""일별 결과 보관 (archive/YYYY-MM-DD_<주제 slug>.json / .md)."""
import json
from datetime import datetime

from . import config

KEEP = ("source", "category", "kind", "title", "link", "date", "score", "is_focus", "is_release",
        "release", "stage1", "summary_data", "related", "uid")


def _export(a):
    d = {k: a.get(k) for k in KEEP}
    d["body"] = (a.get("body") or "")[:3000]
    return d


def save(day, result, stats):
    config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stem = config.ARCHIVE_DIR / f"{day.isoformat()}_{config.SUBJECT.slug}"
    data = {
        "subject": config.SUBJECT.key,
        "date": day.isoformat(),
        "window": [d.isoformat() for d in sorted(config.TARGET_DATES)],
        "generated": datetime.now(config.KST).isoformat(timespec="seconds"),
        "models": {"stage1": config.STAGE1_MODEL, "stage2": config.STAGE2_MODEL},
        "top3": result["top3"],
        "cards": [_export(a) for a in result["cards"]],
        "headlines": [_export(a) for a in result["headlines"]],
        "releases": [_export(a) for a in result["releases"]],
        "source_stats": stats,
    }
    stem.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def title(a):
        return (a.get("summary_data") or {}).get("korean_title") or (a.get("stage1") or {}).get("korean_title") or a["title"]

    lines = ["---", f"date: {day}", f"type: {config.SUBJECT.key}-monitoring",
             f"generated: {data['generated']}", "---", "",
             f"# {config.SUBJECT.title} {day}", ""]
    if result["top3"]:
        lines += ["## 핵심 3줄", *[f"- {t}" for t in result["top3"]], ""]
    for label, items in (("카드", result["cards"]), ("헤드라인", result["headlines"]), ("릴리스·공시", result["releases"])):
        if not items:
            continue
        lines += [f"## {label} ({len(items)})", ""]
        for a in items:
            focus = f" · ⭐{config.SUBJECT.focus_short}" if a.get("is_focus") else ""
            lines.append(f"- [{title(a)}]({a['link']}) — {a['source']} · {a['score']}/10{focus}")
            summary = (a.get("summary_data") or {}).get("korean_summary") or (a.get("stage1") or {}).get("korean_summary")
            if summary:
                lines.append(f"  - {summary}")
        lines.append("")
    stem.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return stem
