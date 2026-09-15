"""소스 레지스트리 — 소스 추가는 SOURCES에 한 줄.

kind
  feed   : 일반 RSS/Atom (YouTube, Reddit, HN 포함)
  gnews  : Google News 검색 RSS (제목 끝 " - 매체명" 분리, 카드 승격 시 원문 URL 복원)
  sec    : SEC EDGAR 공시 Atom (연락처 UA 필요)
  github : GitHub 릴리스 Atom
  hf     : Hugging Face 모델 목록 JSON
category
  official | filing | release | media | kr | community
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    kind: str = "feed"
    category: str = "media"
    weight: int = 0          # Stage1 점수 보정
    prefilter: bool = True   # Stage0 NVIDIA 키워드 필터 적용 여부
    auto_boost: bool = False  # 자동차·로봇 전용 피드 → 무조건 자동차 섹션 후보
    fetch_full: bool = True  # RSS 본문이 짧으면 원문 페이지에서 보강
    ua: str = "browser"      # browser | simple | bot | sec
    enabled: bool = True
    note: str = ""


GITHUB_REPOS = [
    "NVIDIA/TensorRT", "NVIDIA/TensorRT-LLM", "NVIDIA/NeMo", "NVIDIA/Megatron-LM",
    "NVIDIA/cutlass", "NVIDIA/DALI", "NVIDIA/Isaac-GR00T", "isaac-sim/IsaacLab",
    "nvidia-cosmos/cosmos-predict2.5", "triton-inference-server/server", "NVlabs/VILA",
]

SEC_8K = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810"
          "&type=8-K&dateb=&owner=include&count=20&output=atom")
GNEWS = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="

SOURCES = [
    # ── NVIDIA 공식 (1차 출처) ──
    Source("NVIDIA Newsroom", "https://nvidianews.nvidia.com/releases.xml", category="official", weight=1, prefilter=False),
    Source("NVIDIA Blog", "https://blogs.nvidia.com/feed/", category="official", weight=1, prefilter=False),
    Source("NVIDIA Blog · Auto", "https://blogs.nvidia.com/blog/category/auto/feed/", category="official", weight=1, prefilter=False, auto_boost=True),
    Source("NVIDIA Technical Blog", "https://developer.nvidia.com/blog/feed/", category="official", prefilter=False),
    Source("NVIDIA Technical Blog · AV", "https://developer.nvidia.com/blog/category/autonomous-vehicles/feed/", category="official", prefilter=False, auto_boost=True,
           enabled=False, note="2026-09-15 확인 시 엔트리 0건인 빈 피드. 전체 Technical Blog + 자동차 키워드로 커버"),
    Source("NVIDIA Technical Blog · DRIVE", "https://developer.nvidia.com/blog/tag/nvidia-drive/feed/", category="official", prefilter=False, auto_boost=True,
           enabled=False, note="2026-09-15 확인 시 엔트리 0건인 빈 피드"),
    Source("NVIDIA Research", "https://research.nvidia.com/rss.xml", category="official", prefilter=False, enabled=False,
           note="2026-09-15 확인 시 피드에 2021년 글만 있음 (갱신 중단)"),
    Source("YouTube · NVIDIA", "https://www.youtube.com/feeds/videos.xml?channel_id=UCHuiy8bXnmK5nisYHUd1J5g", category="official", prefilter=False, fetch_full=False),
    Source("SEC EDGAR 8-K", SEC_8K, kind="sec", category="filing", weight=1, prefilter=False, fetch_full=False, ua="sec"),
    Source("Hugging Face · nvidia", "https://huggingface.co/api/models?author=nvidia&sort=lastModified&limit=100", kind="hf", category="release", prefilter=False, fetch_full=False),
    *[Source(f"GitHub · {r}", f"https://github.com/{r}/releases.atom", kind="github", category="release", prefilter=False, fetch_full=False)
      for r in GITHUB_REPOS],

    # ── 해외 매체 ──
    Source("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
    Source("The Next Platform", "https://www.nextplatform.com/feed/", weight=1),
    Source("ServeTheHome", "https://www.servethehome.com/feed/"),
    Source("SemiAnalysis", "https://semianalysis.com/feed/", weight=1),
    Source("TechCrunch · nvidia", "https://techcrunch.com/tag/nvidia/feed/"),
    Source("The Verge · nvidia", "https://www.theverge.com/rss/nvidia/index.xml"),
    Source("Ars Technica · nvidia", "https://arstechnica.com/tag/nvidia/feed/"),
    Source("EE Times", "https://www.eetimes.com/feed/"),
    Source("DataCenterDynamics", "https://www.datacenterdynamics.com/en/rss/"),
    Source("CNBC Tech", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),
    Source("Google News · NVIDIA", GNEWS + "NVIDIA+when:2d", kind="gnews", fetch_full=False),
    Source("Google News · NVIDIA 자동차/로봇", GNEWS + "%22NVIDIA+DRIVE%22+OR+%22NVIDIA+Isaac%22+OR+Alpamayo+OR+%22DRIVE+Thor%22+OR+%22Jetson+Thor%22+OR+%22NVIDIA+Cosmos%22+when:2d",
           kind="gnews", fetch_full=False, auto_boost=True),

    # ── 한국 매체 ──
    Source("디일렉", "https://www.thelec.kr/rss/allArticle.xml", category="kr"),
    Source("전자신문", "https://rss.etnews.com/Section902.xml", category="kr"),
    Source("IT조선", "https://it.chosun.com/rss/allArticle.xml", category="kr"),
    Source("한국경제 IT", "https://www.hankyung.com/feed/it", category="kr", ua="simple", note="전체 Chrome UA는 403, 짧은 UA는 200"),

    # ── 커뮤니티 신호 ──
    Source("Hacker News", "https://hnrss.org/newest?q=nvidia", category="community", weight=-1, fetch_full=False),
    Source("Reddit r/nvidia", "https://www.reddit.com/r/nvidia/new/.rss", category="community", weight=-1, fetch_full=False, ua="bot"),
]
