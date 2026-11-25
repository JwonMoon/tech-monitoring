"""GitHub 조직 감시(crawl.crawl_github_org) · 고정 보드(pin) 회귀 — 네트워크·LLM 없이 돈다.

  python tests/test_github_org.py

계약:
- 스냅샷에 없던 저장소만 '신규 공개'. 포크·아카이브 제외. 스냅샷이 비어 있는 첫 실행은
  최근 GH_NEW_FIRST_RUN_DAYS 일 안에 생성된 저장소만 신규 (수백 건 폭주 방지).
- 스타가 GH_SURGE_MIN 이상 또는 GH_SURGE_PCT 이상(절대 GH_SURGE_PCT_MIN 이상) 늘면 '급상승'.
- 기간 내 push 된 인기 저장소는 릴리스 Atom 추가 확인 후보. 주제가 이미 github 소스로 보는 저장소는 제외.
- pin 소스의 글은 점수와 무관하게 카드 아니면 보드로 간다 (헤드라인 상한에 밀리지 않음).
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("SUBJECT", "nvidia")

from techmon import config, crawl, pipeline, render  # noqa: E402

FAILS = []


def check(cond, msg):
    print(f"  {'OK ' if cond else 'FAIL'} {msg}")
    if not cond:
        FAILS.append(msg)


def repo(name, stars=10, created="2026-01-01", pushed=None, fork=False, archived=False):
    pushed = pushed or f"{config.BASE_DATE.isoformat()}T01:00:00Z"
    return {"full_name": name, "stargazers_count": stars, "created_at": f"{created}T00:00:00Z",
            "pushed_at": pushed, "fork": fork, "archived": archived, "private": False, "disabled": False,
            "description": f"{name} desc", "language": "Python", "topics": ["ai"],
            "html_url": f"https://github.com/{name}"}


def test_detect():
    print("\n=== detect_org_changes ===")
    today = config.BASE_DATE
    old_push = (today - timedelta(days=30)).isoformat() + "T00:00:00Z"
    snap = {"repos": {
        "NVIDIA/TensorRT": {"stars": 10000, "created": "2019-05-01", "seen": "2026-11-24"},
        "NVIDIA/quiet": {"stars": 100, "created": "2024-01-01", "seen": "2026-11-24"},
        "NVIDIA/popular": {"stars": 2000, "created": "2023-01-01", "seen": "2026-11-24"},
    }}
    repos = [
        repo("NVIDIA/TensorRT", stars=10050),                  # 기존, +50 — 급상승 아님(150 미만, 0.5%)
        repo("NVIDIA/quiet", stars=160, pushed=old_push),      # +60, 60% — 급상승 (절대 40 이상·25% 이상)
        repo("NVIDIA/popular", stars=2100),                    # +100 (5%) — 급상승 아님, push 기간 내 → 릴리스 후보
        repo("NVIDIA/auto-ontology", stars=3, created="2026-03-01"),  # 스냅샷에 없음 → 신규 (생성일이 오래돼도)
        repo("NVIDIA/some-fork", fork=True),                   # 포크 → 제외
        repo("NVIDIA/old-archive", archived=True),             # 아카이브 → 제외
    ]
    new, surge, rel = crawl.detect_org_changes("NVIDIA", repos, snap, today, fixed_repos=["NVIDIA/TensorRT"])
    check([r["full_name"] for r in new] == ["NVIDIA/auto-ontology"], f"신규 = auto-ontology 만 (실제 {[r['full_name'] for r in new]})")
    check([(r["full_name"], o, n) for r, o, n in surge] == [("NVIDIA/quiet", 100, 160)], f"급상승 = quiet 100→160 (실제 {[(r['full_name'], o, n) for r, o, n in surge]})")
    check([r["full_name"] for r in rel] == ["NVIDIA/popular"], f"릴리스 후보 = popular 만 (TensorRT 는 고정 목록, quiet 는 push 오래됨·스타 부족) 실제 {[r['full_name'] for r in rel]}")
    check(snap["repos"]["NVIDIA/auto-ontology"]["stars"] == 3 and snap["repos"]["NVIDIA/auto-ontology"]["seen"] == today.isoformat(),
          "스냅샷에 신규 저장소가 기록됨")
    check(snap["repos"]["NVIDIA/TensorRT"]["stars"] == 10050, "스냅샷 스타 수 갱신")
    check("NVIDIA/some-fork" in snap["repos"], "포크도 스냅샷에는 기록 (다음 날 신규로 다시 뜨지 않게)")

    # 첫 실행: 스냅샷에 이 조직이 없으면 최근 생성분만 신규
    fresh = {"repos": {"NVlabs/x": {"stars": 1, "created": "2020-01-01", "seen": "2026-11-24"}}}
    recent = (today - timedelta(days=2)).isoformat()
    new2, _, _ = crawl.detect_org_changes("NVIDIA", [repo("NVIDIA/ancient", created="2018-01-01"),
                                                     repo("NVIDIA/brand-new", created=recent)], fresh, today)
    check([r["full_name"] for r in new2] == ["NVIDIA/brand-new"], f"첫 실행은 최근 생성분만 신규 (실제 {[r['full_name'] for r in new2]})")
    check("NVIDIA/ancient" in fresh["repos"], "첫 실행에도 전체 목록이 스냅샷에 들어감")
    # 둘째 날: 같은 목록이면 신규 0
    new3, surge3, _ = crawl.detect_org_changes("NVIDIA", [repo("NVIDIA/ancient", created="2018-01-01"),
                                                          repo("NVIDIA/brand-new", created=recent)], fresh, today)
    check(not new3 and not surge3, "같은 목록 재실행은 신규·급상승 0")


def test_crawl_mocked(monkey):
    print("\n=== crawl_github_org (API·README·Atom 모킹) ===")
    today = config.BASE_DATE
    atom = f'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>v2.0.0</title><updated>{today.isoformat()}T03:00:00Z</updated>
<link rel="alternate" href="https://github.com/NVIDIA/popular/releases/tag/v2.0.0"/><content>big release</content></entry></feed>'''

    class R:
        def __init__(self, text, content=None):
            self.text, self.content = text, (content if content is not None else text.encode())

    def fake_pages(url, ua, max_pages):
        check("orgs/NVIDIA/repos" in url, "조직 URL 로 호출")
        return [repo("NVIDIA/auto-ontology", created="2026-03-01"), repo("NVIDIA/popular", stars=2100)], True

    def fake_get(url, ua="browser", timeout=20):
        if "raw.githubusercontent.com/NVIDIA/auto-ontology" in url:
            return R("# Auto Ontology\n\n[![badge](x.svg)](y) Builds **ontologies** automatically. ![img](a.png)")
        if url.endswith("NVIDIA/popular/releases.atom"):
            return R(atom)
        raise AssertionError(f"예상 밖 요청 {url}")

    monkey(crawl, "_gh_api_pages", fake_pages)
    monkey(crawl, "http_get", fake_get)
    from techmon import state
    state._github = {"repos": {"NVIDIA/popular": {"stars": 2000, "created": "2023-01-01", "seen": "2026-11-24"}}}
    src = next(s for s in config.SUBJECT.sources if s.kind == "github_org")
    raw, items = crawl.crawl_github_org(src)
    kinds = [(a["release"]["type"], a["release"]["name"]) for a in items]
    check(raw == 2, "raw = 저장소 수")
    check(("GitHub·신규 저장소", "NVIDIA/auto-ontology") in kinds, f"신규 저장소 항목 생성 {kinds}")
    check(("GitHub", "NVIDIA/popular") in kinds, "인기 저장소 릴리스 v2.0.0 추가 수집")
    new = next(a for a in items if a["release"]["type"] == "GitHub·신규 저장소")
    check(new["uid"] == "ghnew:NVIDIA/auto-ontology" and new["is_release"], "uid 는 ghnew:저장소, 릴리스 보드 경로")
    check("Builds ontologies automatically" in new["body"] and "badge" not in new["body"], f"README 발췌에서 배지·이미지 제거: {new['body'][-120:]}")
    check(new["prefilter"] is False and new["category"] == "release", "사전필터 면제 · release 카테고리")
    rel = next(a for a in items if a["release"]["type"] == "GitHub")
    check(rel["uid"] == "gh:NVIDIA/popular:v2.0.0", "릴리스 uid 는 기존 github 소스와 같은 형식 (중복 발송 방지)")


def test_pin_boards():
    print("\n=== classify: pin 보드 ===")

    def art(title, score, pin="", is_release=False, category="official"):
        return {"title": title, "body": "", "score": score, "is_focus": False, "is_release": is_release,
                "category": category, "kind": "feed", "pin": pin, "release": None, "uid": title,
                "stage1": {"korean_title": title, "korean_summary": ""}}

    arts = [art("blog-high", 7, pin="기술 블로그"), art("blog-low", 1, pin="기술 블로그"),
            art("blog-mid", 3, pin="기술 블로그"), art("news-low", 1), art("news-mid", 3)]
    cards, heads, rels, boards = pipeline.classify(arts)
    check([a["title"] for a in cards] == ["blog-high"], "7점 블로그 글은 카드")
    check([a["title"] for a in boards.get("기술 블로그", [])] == ["blog-mid", "blog-low"],
          f"카드 아닌 블로그 글은 점수 무관하게 보드 (실제 {[a['title'] for a in boards.get('기술 블로그', [])]})")
    check([a["title"] for a in heads] == ["news-mid"], "일반 글은 종전대로 — 1점은 탈락, 3점은 헤드라인")

    print("\n=== render: 보드·신규 저장소 섹션 ===")
    for a in arts:
        a.update({"source": "NVIDIA Technical Blog", "link": "https://developer.nvidia.com/blog/x", "date": "2026-11-25 09:00",
                  "topic": "Software-SDK", "summary_data": None})
    newrepo = art("NVIDIA/auto-ontology 신규 공개 저장소", 5, is_release=True, category="release")
    newrepo.update({"source": "GitHub · 신규 저장소", "link": "https://github.com/NVIDIA/auto-ontology", "date": "2026-11-25 06:00",
                    "topic": "Research-Models", "summary_data": None,
                    "release": {"type": "GitHub·신규 저장소", "name": "NVIDIA/auto-ontology", "version": "★3"}})
    oldrel = art("NVIDIA/TensorRT v10", 6, is_release=True, category="release")
    oldrel.update({"source": "GitHub", "link": "https://github.com/NVIDIA/TensorRT", "date": "2026-11-25 06:00",
                   "topic": "Software-SDK", "summary_data": None,
                   "release": {"type": "GitHub", "name": "NVIDIA/TensorRT", "version": "v10"}})
    result = {"cards": cards, "headlines": heads, "releases": [oldrel, newrepo], "boards": boards, "top3": [], "omitted": 0}
    html = render.build(result, [])
    check("📝 기술 블로그" in html and "blog-low" in html, "보드 섹션이 렌더되고 1점 글도 보임")
    check(html.index("auto-ontology") < html.index("NVIDIA/TensorRT</a>"), "릴리스 보드에서 신규 저장소가 기존 릴리스보다 위")
    subj = render.subject(result)
    check("신규 저장소 1" in subj and "추가 3" in subj, f"제목줄에 신규 저장소 수·보드 포함 추가 수: {subj}")


if __name__ == "__main__":
    import unittest.mock as um
    patches = []

    def monkey(obj, name, value):
        p = um.patch.object(obj, name, value)
        p.start()
        patches.append(p)

    try:
        test_detect()
        test_crawl_mocked(monkey)
        test_pin_boards()
    finally:
        for p in patches:
            p.stop()
    print(f"\n{'실패 ' + str(len(FAILS)) + '건' if FAILS else '전부 통과'}")
    sys.exit(1 if FAILS else 0)
