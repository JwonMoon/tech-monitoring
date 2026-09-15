"""Stage 0 → Stage 1 → 가중·병합 → 분류 → Stage 2 → TOP3."""
import difflib
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import config, crawl, filters, prompts
from .llm import call_llm, parse_json, parse_json_array

TOPIC_KEYS = [t.strip() for t in prompts.TOPICS.split("|")]
CATEGORY_RANK = {"official": 0, "filing": 1, "release": 2, "media": 3, "kr": 4, "community": 6}


def log(msg):
    print(msg, flush=True)


def deadline_exceeded():
    return (time.time() - config.START_TS) / 60 > config.SOFT_DEADLINE_MIN


def _rank(a):
    r = CATEGORY_RANK.get(a["category"], 9)
    if a["kind"] == "gnews":
        r = 5
    return (r, -len(a.get("body") or ""))


def _norm(t):
    return re.sub(r"[^\w가-힣]+", " ", (t or "").lower()).strip()


def merge_duplicates(articles, key, threshold, same_topic=False):
    """제목 유사도로 같은 소식을 묶는다. 대표는 공식 > 공시 > 매체 > 국내 > Google News > 커뮤니티 순."""
    groups = []
    for a in sorted(articles, key=_rank):
        k = _norm(key(a))
        placed = False
        for g in groups:
            rep = g[0]
            if a["uid"] and a["uid"] == rep["uid"]:
                g.append(a)
                placed = True
                break
            if a["is_release"] or rep["is_release"] or len(k) < 15:
                continue
            if same_topic and a.get("topic") != rep.get("topic"):
                continue
            if difflib.SequenceMatcher(None, k, _norm(key(rep))).ratio() >= threshold:
                g.append(a)
                placed = True
                break
        if not placed:
            groups.append([a])
    out = []
    for g in groups:
        rep = g[0]
        rep.setdefault("related", [])
        rep.setdefault("member_uids", [rep["uid"]])
        for o in g[1:]:
            rep["related"].append({"source": o["source"], "title": o["title"], "link": o["link"]})
            rep["related"].extend(o.get("related") or [])
            rep["member_uids"].extend(o.get("member_uids") or [o["uid"]])
            rep["auto_hint"] = rep["auto_hint"] or o["auto_hint"]
            if "stage1" in o and "stage1" in rep:
                rep["stage1"]["score"] = max(rep["stage1"]["score"], o["stage1"]["score"])
                rep["stage1"]["is_auto"] = rep["stage1"]["is_auto"] or o["stage1"]["is_auto"]
        out.append(rep)
    return out


def stage0(articles):
    kept, counts = [], {}
    for a in articles:
        verdict, _reason = filters.pre_filter(a)
        counts[a["source_group"]] = counts.get(a["source_group"], [0, 0])
        counts[a["source_group"]][0] += 1
        if verdict == "pass":
            kept.append(a)
            counts[a["source_group"]][1] += 1
    return kept, counts


def _stage1_item(i, a):
    tag = "[공시] " if a["kind"] == "sec" else "[릴리스] " if a["is_release"] else \
          "[커뮤니티] " if a["category"] == "community" else ""
    return f"[{i}] {tag}출처: {a['source']}\n제목: {a['title']}\n본문: {(a['body'] or '(본문 없음)')[:900]}"


def _coerce_score(v):
    try:
        return max(0, min(10, int(round(float(v)))))
    except (TypeError, ValueError):
        return None


def _fallback_score(a):
    if a["category"] in ("official", "filing"):
        return 4
    if a["is_release"]:
        return 3
    return config.HEADLINE_SCORE


def stage1(articles):
    size = config.STAGE1_BATCH_SIZE
    n_batches = (len(articles) + size - 1) // size
    log(f"\n[STAGE 1] 배치 채점 — {len(articles)}건 / {n_batches}배치 ({config.STAGE1_MODEL}, 동시 {config.STAGE1_WORKERS})")
    batches = [(b // size + 1, articles[b:b + size]) for b in range(0, len(articles), size)]
    with ThreadPoolExecutor(max_workers=config.STAGE1_WORKERS) as ex:
        list(ex.map(lambda nb: _score_batch(nb[0], nb[1], n_batches), batches))


def _score_batch(no, batch, n_batches):
    prompt = prompts.STAGE1.replace("__TOPICS__", prompts.TOPICS).replace(
        "__ITEMS__", "\n\n".join(_stage1_item(i, a) for i, a in enumerate(batch)))
    arr = None
    for attempt in range(2):
        arr = parse_json_array(call_llm(prompt, config.STAGE1_MODEL, timeout=300))
        if arr is not None:
            break
        log("    [!] 배치 파싱 실패, 재시도" if attempt == 0 else "    [!] 배치 최종 실패 — 기본 점수 적용")
    by_id = {}
    for obj in arr or []:
        if isinstance(obj, dict):
            try:
                by_id[int(obj.get("id"))] = obj
            except (TypeError, ValueError):
                pass
    for i, a in enumerate(batch):
        obj = by_id.get(i)
        score = _coerce_score(obj.get("score")) if obj else None
        a["stage1"] = {
            "parsed": score is not None,
            "score": score if score is not None else _fallback_score(a),
            "article_type": (obj or {}).get("article_type") or "",
            "is_auto": bool((obj or {}).get("is_auto")),
            "signal_tags": (obj or {}).get("signal_tags") or [],
            "korean_title": (obj or {}).get("korean_title") or "",
            "korean_summary": (obj or {}).get("korean_summary") or "",
        }
    log(f"  배치 {no}/{n_batches} 완료")


def _topic(a):
    if a["is_auto"]:
        return "Automotive-Robotics"
    at = (a["stage1"].get("article_type") or "").lower()
    for k in TOPIC_KEYS:
        if k.lower() in at or (at and at in k.lower()):
            return k
    return "Community-Signal" if a["category"] == "community" else "기타"


def adjust(articles):
    """소스 가중 + 자동차·로봇 가중. 자동차 제목 신호가 있으면 헤드라인 이하로 떨어지지 않음."""
    for a in articles:
        s1 = a["stage1"]
        score = s1["score"] + (a["weight"] if s1["parsed"] else 0)
        a["is_auto"] = s1["is_auto"] or filters.is_auto(a)
        if a["is_auto"]:
            score += 1
            if a["auto_hint"] or filters.AUTO_KW.search(a["title"]) or s1["is_auto"]:
                score = max(score, config.HEADLINE_SCORE)
        a["score"] = max(0, min(10, score))
        a["topic"] = _topic(a)


def classify(articles):
    cards, headlines, releases = [], [], []
    for a in sorted(articles, key=lambda x: (-x["score"], _rank(x))):
        s = a["score"]
        if a["is_release"]:
            if s >= config.RELEASE_MAJOR_SCORE:
                cards.append(a)
            elif s >= 1:
                releases.append(a)
            continue
        need = (config.COMMUNITY_MAJOR_SCORE if a["category"] == "community"
                else config.AUTO_MAJOR_SCORE if a["is_auto"] else config.MAJOR_SCORE)
        if s >= need:
            cards.append(a)
        elif s >= config.HEADLINE_SCORE:
            headlines.append(a)
    auto = [c for c in cards if c["is_auto"]]
    other = [c for c in cards if not c["is_auto"]]
    kept = auto[:config.MAX_AUTO_CARDS] + other[:config.MAX_CARDS]
    demoted = [c for c in cards if c not in kept]
    headlines = sorted(demoted + headlines, key=lambda x: -x["score"])
    return sorted(kept, key=lambda x: -x["score"]), headlines, releases[:config.MAX_RELEASES]


def _ensure_body(a):
    """Google News 등 본문이 없는 카드는 원문 URL을 복원해 본문 확보. 실패 시 False."""
    if len(a["body"]) >= 300:
        return True
    link = a["link"]
    if a["kind"] == "gnews":
        link = crawl.resolve_gnews_url(a["link"]) or ""
        if link:
            a["link"] = link
    if link:
        full = crawl.fetch_full_text(link)
        if len(full) > len(a["body"]):
            a["body"] = full[:6000]
    return len(a["body"]) >= 300 or a["is_release"]


def _analyze(i, a, total):
    """카드 1건 심층 분석. 반환: 'card' | 'headline'."""
    if deadline_exceeded():
        log(f"  [{i}] 시간 한도({config.SOFT_DEADLINE_MIN}분) 초과 → 헤드라인: {a['title'][:60]}")
        return "headline"
    if not _ensure_body(a):
        log(f"  [{i}] 본문 확보 실패 → 헤드라인: {a['title'][:60]}")
        return "headline"
    prompt = (prompts.STAGE2
              .replace("__AUTO_RULE__", prompts.AUTO_RULE_ON if a["is_auto"] else prompts.AUTO_RULE_OFF)
              .replace("__SOURCE__", a["source"]).replace("__TITLE__", a["title"])
              .replace("__BODY__", a["body"][:5000]))
    sd = None
    for _attempt in range(2):
        sd = parse_json(call_llm(prompt, config.STAGE2_MODEL, timeout=300))
        if sd and sd.get("korean_title"):
            break
        sd = None
    a["summary_data"] = sd
    log(f"  [{i}/{total}] {'✓' if sd else '✗'} ({a['score']}/10) {a['title'][:60]}")
    return "card"


def stage2(cards, headlines):
    log(f"\n[STAGE 2] 카드 심층 분석 — {len(cards)}건 ({config.STAGE2_MODEL}, 동시 {config.STAGE2_WORKERS})")
    with ThreadPoolExecutor(max_workers=config.STAGE2_WORKERS) as ex:
        verdicts = list(ex.map(lambda ia: _analyze(ia[0], ia[1], len(cards)), enumerate(cards, 1)))
    final = [a for a, v in zip(cards, verdicts) if v == "card"]
    headlines.extend(a for a, v in zip(cards, verdicts) if v != "card")
    headlines.sort(key=lambda x: -x["score"])
    return final, headlines


def top3(cards):
    if not cards:
        return []
    lines = []
    for a in cards[:15]:
        sd = a.get("summary_data") or {}
        title = sd.get("korean_title") or a["stage1"].get("korean_title") or a["title"]
        summary = sd.get("korean_summary") or a["stage1"].get("korean_summary") or ""
        lines.append(f"- {'[AUTO] ' if a['is_auto'] else ''}{title} :: {summary}")
    obj = parse_json(call_llm(prompts.TOP3.replace("__DIGEST__", "\n".join(lines)), config.STAGE2_MODEL, timeout=180))
    picked = [str(x).strip() for x in (obj or {}).get("top3", []) if str(x).strip()]
    if picked:
        return [re.sub(r"\s*::.*$", "", x) for x in picked[:3]]
    return [((a.get("summary_data") or {}).get("korean_summary") or a["stage1"].get("korean_summary"))
            for a in cards[:3] if (a.get("summary_data") or a["stage1"].get("korean_summary"))]


def run(articles):
    kept, stage0_counts = stage0(articles)
    log(f"\n[STAGE 0] 사전필터: {len(articles)} → {len(kept)}건")
    kept = merge_duplicates(kept, key=lambda a: a["title"], threshold=0.85)
    log(f"  제목 병합 후 {len(kept)}건")
    if config.MAX_ARTICLES:
        kept = sorted(kept, key=_rank)[:config.MAX_ARTICLES]
        log(f"  ⚠️ 테스트 모드: {len(kept)}건만 채점")
    if kept:
        stage1(kept)
        adjust(kept)
        before = len(kept)
        kept = merge_duplicates(kept, key=lambda a: a["stage1"]["korean_title"] or a["title"],
                                threshold=0.8, same_topic=True)
        if len(kept) != before:
            log(f"  한국어 제목 2차 병합: {before} → {len(kept)}건")
            adjust(kept)
    cards, headlines, releases = classify(kept)
    log(f"\n[분류] 카드 {len(cards)} (자동차·로봇 {sum(c['is_auto'] for c in cards)}) · "
        f"헤드라인 {len(headlines)} · 릴리스/공시 {len(releases)}")
    cards, headlines = stage2(cards, headlines)
    return {"cards": cards, "headlines": headlines, "releases": releases,
            "top3": top3(cards), "scored": kept, "stage0_counts": stage0_counts}
