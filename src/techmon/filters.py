"""Stage 0 사전필터 (정규식, LLM 비용 없음). 키워드는 주제(Subject.keywords)에서 온다."""


def is_focus(article, kw):
    """중점 분야(자동차·로봇 / 사업·배치 ...) 판정."""
    if article.get("focus_hint"):
        return True
    if kw.focus_specific.search(f"{article['title']} {article['body'][:1500]}"):
        return True
    return bool(kw.focus_generic.search(article["title"]))


def focus_in_title(article, kw):
    """제목만으로 중점 분야가 드러나는지 (가중 시 헤드라인 보존 근거)."""
    return bool(kw.focus_specific.search(article["title"]) or kw.focus_generic.search(article["title"]))


def _only_ambiguous(kw, hits):
    """강한 신호가 전부 오탐 잦은 표현(예: "Tier IV")에서만 나왔는가."""
    return bool(kw.ambiguous) and all(kw.ambiguous.fullmatch(h) for h in hits)


def pre_filter(article, kw):
    """('pass'|'skip'|'reject', 이유)"""
    if not article.get("prefilter", True):
        return "pass", "공식·공시·릴리스 소스"
    title = article["title"]
    text = f"{title} {article['body']}"
    strong = kw.strong.findall(text)
    if not strong:
        return "skip", "주제 신호 없음"
    # "Tier IV"는 데이터센터 등급·배출가스 규제에도 쓰인다. 그 표현만 걸렸는데 해당 문맥까지
    # 보이면 다른 주제의 기사로 보고 버린다.
    if kw.ambiguous_noise and _only_ambiguous(kw, strong) and kw.ambiguous_noise.search(text):
        return "reject", "동음이의 표현 (다른 주제)"
    if (not kw.strong.search(title) and len(strong) < 2
            and not (kw.business.search(text) or kw.focus_specific.search(text)
                     or kw.focus_generic.search(title))):
        return "skip", "지나가는 언급"
    if kw.exclude_title.search(title) and not (kw.focus_specific.search(text)
                                               or kw.focus_generic.search(title)):
        return "reject", "딜·홍보성"
    return "pass", "주제 신호"
