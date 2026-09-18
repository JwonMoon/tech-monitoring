"""Stage 0 → Stage 1 → 가중·병합 → 분류 → Stage 2 → TOP3."""
import difflib
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import config, crawl, filters, prompts
from .llm import STATUS as LLM_STATUS, call_llm, parse_json, parse_json_array

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
            rep["focus_hint"] = rep["focus_hint"] or o["focus_hint"]
            if "stage1" in o and "stage1" in rep:
                rep["stage1"]["score"] = max(rep["stage1"]["score"], o["stage1"]["score"])
                rep["stage1"]["is_focus"] = rep["stage1"]["is_focus"] or o["stage1"]["is_focus"]
        out.append(rep)
    return out


def stage0(articles):
    kept, counts = [], {}
    for a in articles:
        verdict, _reason = filters.pre_filter(a, config.SUBJECT.keywords)
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
    prompt = prompts.stage1(config.SUBJECT, "\n\n".join(_stage1_item(i, a) for i, a in enumerate(batch)))
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
            "is_focus": bool((obj or {}).get("is_focus")),
            "signal_tags": (obj or {}).get("signal_tags") or [],
            "korean_title": (obj or {}).get("korean_title") or "",
            "korean_summary": (obj or {}).get("korean_summary") or "",
        }
    log(f"  배치 {no}/{n_batches} 완료")


def _topic(a):
    """LLM 이 고른 article_type 을 먼저 믿는다.

    중점 분야가 여러 개일 수 있으므로 '중점이면 무조건 그 토픽'으로 강제하지 않는다.
    매핑에 실패했을 때만 중점 신호를 보고 첫 중점 토픽으로 보정한다.
    """
    at = (a["stage1"].get("article_type") or "").lower()
    for k in config.SUBJECT.topic_keys:
        if k.lower() in at or (at and at in k.lower()):
            return k
    if a.get("focus_signal"):
        return config.SUBJECT.focus_keys[0]
    return "Community-Signal" if a["category"] == "community" else "기타"


def adjust(articles):
    """소스 가중 + 중점 분야 가중. 제목에 중점 신호가 있으면 헤드라인 이하로 떨어지지 않음.

    중점 판정은 '토픽이 중점 토픽인가'로 정한다. 키워드·전용 피드·LLM 플래그는
    토픽 매핑이 실패했을 때의 보정 신호(focus_signal)로만 쓴다.
    """
    kw = config.SUBJECT.keywords
    focus_keys = set(config.SUBJECT.focus_keys)
    for a in articles:
        s1 = a["stage1"]
        score = s1["score"] + (a["weight"] if s1["parsed"] else 0)
        a["focus_signal"] = s1["is_focus"] or filters.is_focus(a, kw)
        a["topic"] = _topic(a)
        a["is_focus"] = a["topic"] in focus_keys
        if a["is_focus"]:
            score += 1
            if a["focus_hint"] or filters.focus_in_title(a, kw) or s1["is_focus"]:
                score = max(score, config.HEADLINE_SCORE)
        a["score"] = max(0, min(10, score))


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
                else config.FOCUS_MAJOR_SCORE if a["is_focus"] else config.MAJOR_SCORE)
        if s >= need:
            cards.append(a)
        elif s >= config.HEADLINE_SCORE:
            headlines.append(a)
    focus = [c for c in cards if c["is_focus"]]
    other = [c for c in cards if not c["is_focus"]]
    kept = focus[:config.MAX_FOCUS_CARDS] + other[:config.MAX_CARDS]
    demoted = [c for c in cards if c not in kept]
    headlines = sorted(demoted + headlines, key=lambda x: -x["score"])
    return sorted(kept, key=lambda x: -x["score"]), headlines, releases[:config.MAX_RELEASES]


def cap_headlines(headlines):
    """중점 분야 헤드라인은 전부 유지, 나머지는 점수순 MAX_HEADLINES건. 반환: (유지, 생략 건수)"""
    focus = [h for h in headlines if h["is_focus"]]
    other = [h for h in headlines if not h["is_focus"]]
    kept = focus + other[:config.MAX_HEADLINES]
    return sorted(kept, key=lambda x: -x["score"]), len(other) - len(other[:config.MAX_HEADLINES])


def _ensure_body(a):
    """본문이 짧은 카드(주로 Google News)의 본문 확보. 반환: (성공 여부, 실패 사유)
    1) Google News 링크면 원문 URL 복원 후 추출
    2) 실패하면 병합된 '관련 보도' 중 Google News가 아닌 링크에서 추출"""
    if len(a["body"]) >= 300 or a["is_release"]:
        return True, ""
    reason = ""
    link = a["link"]
    if a["kind"] == "gnews":
        link, reason = crawl.resolve_gnews_url(a["link"])
        if link:
            a["link"] = link
    candidates = ([link] if link else []) + [r["link"] for r in a.get("related") or []
                                             if r.get("link") and "news.google.com" not in r["link"]]
    for url in candidates[:4]:
        full = crawl.fetch_full_text(url)
        if len(full) >= 300:
            a["body"] = full[:6000]
            if url != a["link"] and "news.google.com" in a["link"]:
                a["link"] = url
            return True, ""
        reason = reason or f"본문 추출 실패 ({url[:60]})"
    return False, reason or "원문 링크 없음"


def _analyze(i, a, total):
    """카드 1건 심층 분석. 반환: 'card' | 'headline'."""
    if deadline_exceeded():
        log(f"  [{i}] 시간 한도({config.SOFT_DEADLINE_MIN}분) 초과 → 헤드라인: {a['title'][:60]}")
        return "headline"
    ok, reason = _ensure_body(a)
    if not ok:
        # 중요한 소식이 본문 확보 실패로 사라지지 않도록 카드로 남기고 제목·요약만 표시
        a["summary_data"], a["body_missing"] = None, True
        log(f"  [{i}] 본문 확보 실패 → 요약 카드 유지: {a['title'][:60]} | {reason}")
        return "card"
    prompt = prompts.stage2(config.SUBJECT, a["source"], a["title"], a["body"][:5000], a["is_focus"])
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
        lines.append(f"- {'[FOCUS] ' if a['is_focus'] else ''}{title} :: {summary}")
    obj = parse_json(call_llm(prompts.top3(config.SUBJECT, "\n".join(lines)), config.STAGE2_MODEL, timeout=180))
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
    log(f"\n[분류] 카드 {len(cards)} ({config.SUBJECT.focus_short} {sum(c['is_focus'] for c in cards)}) · "
        f"헤드라인 {len(headlines)} · 릴리스/공시 {len(releases)}")
    cards, headlines = stage2(cards, headlines)
    headlines, omitted = cap_headlines(headlines)
    if omitted:
        log(f"  헤드라인 상한 {config.MAX_HEADLINES}건 — 저점 {omitted}건은 archive에만 기록")
    result = {"cards": cards, "headlines": headlines, "releases": releases, "omitted": omitted,
              "top3": top3(cards), "scored": kept, "stage0_counts": stage0_counts}
    result["llm_exhausted"] = LLM_STATUS["exhausted"]
    if LLM_STATUS["exhausted"]:
        log("  [!] LLM 사용 한도 초과로 일부 채점·분석이 생략됨 (메일에 표시)")
    return result
