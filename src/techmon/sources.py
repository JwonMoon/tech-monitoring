"""소스 레코드와 URL 빌더. 실제 소스 목록은 주제별로 subjects/*.py 가 들고 있다.

kind
  feed   : 일반 RSS/Atom (YouTube, Reddit, HN, Discourse, Medium 포함)
  gnews  : Google News 검색 RSS (제목 끝 " - 매체명" 분리, 카드 승격 시 원문 URL 복원)
  sec    : SEC EDGAR 공시 Atom (연락처 UA 필요)
  github : GitHub 릴리스 Atom (저장소 하나)
  github_org : GitHub 조직 저장소 목록 API — 새로 공개된 저장소, 스타 급증, 활발한 인기 저장소의 릴리스
  hf     : Hugging Face 모델 목록 JSON
category
  official | filing | release | media | kr | community
pin
  라벨을 주면 그 소스의 글은 카드로 오르지 않아도 메일 끝 전용 보드에 전부 실린다
  (NVIDIA Technical Blog 처럼 점수와 무관하게 "무엇이 올라왔는지" 매일 봐야 하는 소스).
"""
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    kind: str = "feed"
    category: str = "media"
    weight: int = 0           # Stage1 점수 보정
    prefilter: bool = True    # Stage0 키워드 필터 적용 여부
    focus_boost: bool = False  # 중점 분야 전용 피드 → 무조건 중점 섹션 후보
    fetch_full: bool = True   # RSS 본문이 짧으면 원문 페이지에서 보강
    ua: str = "browser"       # browser | simple | bot | sec
    enabled: bool = True
    note: str = ""
    pin: str = ""             # 전용 보드 라벨 (빈 문자열이면 보드 없음)


def gnews(query, lang="en-US", gl="US", days=2):
    """Google News 검색 RSS. query 는 원문 그대로 주면 여기서 인코딩한다."""
    ceid = f"{gl}:{lang.split('-')[0]}"
    q = quote(f"{query} when:{days}d", safe="")
    return f"https://news.google.com/rss/search?hl={lang}&gl={gl}&ceid={ceid}&q={q}"


def github_releases(repos, category="release", **kw):
    """저장소 목록 → 릴리스 Atom 소스 목록."""
    return [Source(f"GitHub · {r}", f"https://github.com/{r}/releases.atom", kind="github",
                   category=category, prefilter=False, fetch_full=False, **kw) for r in repos]


def github_org(orgs, category="release", **kw):
    """조직 목록 → 조직 저장소 목록 API 소스 목록.

    저장소 이름을 미리 알 필요가 없다. 어제 스냅샷(state/github_<slug>.json)에 없던 저장소가
    나타나면 '신규 공개', 스타가 급증하면 '주목 급상승', 최근 push 가 있는 인기 저장소는
    릴리스 Atom 을 추가로 확인한다. 자세한 건 crawl.crawl_github_org.
    """
    return [Source(f"GitHub 조직 · {o}",
                   f"https://api.github.com/orgs/{o}/repos?type=public&sort=created&direction=desc&per_page=100",
                   kind="github_org", category=category, prefilter=False, fetch_full=False, ua="bot", **kw)
            for o in orgs]
