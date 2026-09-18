"""Wayve 사업·기술 동향.

영국(런던) 기반 자율주행 기업. 규칙 기반 대신 End-to-End 학습으로 가는 'AV2.0' 을 내세우고,
AI Driver 소프트웨어를 OEM 에 공급하는 모델이다. 2026-02 Series D 12억 달러(밸류 86억 달러,
Microsoft·NVIDIA·Uber·Mercedes-Benz·Nissan·Stellantis 참여), Nissan ProPILOT 양산 FY2027,
Uber 런던 자율주행 서비스 개시(2026-09).

중점 분야가 둘이다.
- 사업 · 상용화: 투자·기업가치, OEM 양산 계약, 로보택시 상용 개시, 신규 지역 확장.
- 연구 · 기술: GAIA(월드 모델)·LINGO(설명 가능 주행)·E2E 학습 등 기술 성과.
Wayve 는 이 둘이 서로를 끌어주는 회사라 한쪽만 보면 그림이 안 나온다.

[이름 충돌] WayV(K-pop 그룹), wavve/웨이브(국내 OTT), wave(일반어)와 헷갈릴 수 있지만
철자 'Wayve' 가 셋 다와 달라서 strong 정규식 자체가 방어벽이 된다. Google News 가 유사어를
섞어 줘도 Stage 0 에서 떨어지므로 TIER IV 때와 달리 ambiguous 가드는 쓰지 않는다.
한국어 '웨이브' 는 OTT 와 충돌이 커서 키워드에 넣지 않는다 (국내 기사도 보통 "Wayve" 병기).
"""
import re

from ..sources import Source, github_releases, gnews
from .base import Focus, Keywords, Prompt, Subject

# 전부 논문 코드 저장소다. 2026-09-18 확인 시 releases.atom 이 0건이라 수확은 기대하기 어렵지만,
# 저장소당 요청 1건이라 비용이 미미하고 논문 코드가 태깅되면 그때 잡힌다.
GITHUB_REPOS = [
    "wayveai/fiery",
    "wayveai/Driving-with-LLMs",
    "wayveai/mile",
    "wayveai/LingoQA",
    "wayveai/wayve_scenes",
]

SOURCES = [
    # ── 공식 (1차 출처) ──
    # wayve.ai 는 RSS 를 제공하지 않는다. /press/category/press-release/ 퍼머링크를 보고
    # WordPress 라 추정했지만 틀렸다. 보도자료는 아래 Google News 사업 질의가 잡는다
    # (2026-09-18 실측 7건 전부 사전필터 통과).
    Source("Wayve", "https://wayve.ai/feed/", category="official", weight=1, prefilter=False, ua="simple",
           enabled=False,
           note="2026-09-18 전체 Chrome UA 로 403 → 짧은 UA 로는 200 이지만 엔트리 0건. RSS 가 아니다"),
    Source("Wayve · Press", "https://wayve.ai/press/feed/", category="official", weight=1, prefilter=False, ua="simple",
           enabled=False, note="2026-09-18 위와 동일 — 200 이지만 엔트리 0건"),

    # ── 릴리스 · 연구 ──
    *github_releases(GITHUB_REPOS),
    Source("arXiv · Wayve", "http://export.arxiv.org/api/query?search_query=all:Wayve"
                            "&sortBy=submittedDate&sortOrder=descending&max_results=30",
           category="release", prefilter=False, fetch_full=False,
           note="arXiv API 는 Atom 이라 feed kind 로 파싱된다. GAIA·LINGO 논문 포착용"),

    # ── 해외 매체 ──
    Source("TechCrunch · transportation", "https://techcrunch.com/category/transportation/feed/"),
    Source("The Robot Report", "https://www.therobotreport.com/feed/"),
    Source("IEEE Spectrum · Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss"),
    Source("The Verge", "https://www.theverge.com/rss/index.xml"),
    Source("Google News · Wayve", gnews("Wayve"), kind="gnews", fetch_full=False),
    Source("Google News · Wayve 사업",
           gnews('Wayve funding OR valuation OR Nissan OR Uber OR robotaxi OR "mass production" OR partnership'),
           kind="gnews", fetch_full=False, focus_boost=True),
    Source("Google News · Wayve 연구",
           gnews('Wayve GAIA OR LINGO OR "world model" OR "end-to-end driving" OR "AV2.0"'),
           kind="gnews", fetch_full=False, focus_boost=True),
    # 영국 기업이라 현지 매체(FT·Telegraph·Sifted)는 영국판에서 더 잘 잡힌다.
    Source("Google News · Wayve (UK)", gnews("Wayve autonomous OR self-driving", lang="en-GB", gl="GB"),
           kind="gnews", fetch_full=False),

    # ── 한국 매체 ──
    # '웨이브'는 OTT 와 충돌해서 라틴 표기만 쓴다.
    Source("Google News · Wayve (KR)", gnews("Wayve 자율주행", lang="ko", gl="KR"),
           kind="gnews", category="kr", fetch_full=False),
    Source("디일렉", "https://www.thelec.kr/rss/allArticle.xml", category="kr"),
    Source("전자신문", "https://rss.etnews.com/Section902.xml", category="kr"),

    # ── 커뮤니티 신호 ──
    Source("Hacker News", "https://hnrss.org/newest?q=wayve", category="community", weight=-1, fetch_full=False),
    Source("Reddit r/SelfDrivingCars", "https://www.reddit.com/r/SelfDrivingCars/new/.rss",
           category="community", weight=-1, fetch_full=False, ua="bot"),
]

KEYWORDS = Keywords(
    # 'Wayve' 철자가 WayV·wavve·wave 와 모두 달라 이 자체가 오탐 방어다.
    # GAIA-X(유럽 클라우드)·Gaia DR3(ESA 천문)와 안 겹치도록 GAIA 는 하이픈+숫자로 한정한다.
    strong=re.compile(
        r'\bWayve\b|\bAV ?2\.0\b|Wayve AI Driver|\bGAIA-[12]\b|\bLINGO-[12]\b|'
        r'WayveScenes|LingoQA|Alex Kendall',
        re.IGNORECASE),
    business=re.compile(
        r'\bfunding\b|Series [A-E]\b|valuation|\bIPO\b|\binvest(?:ments?|s|ed|ing)?\b|\bstake\b|'
        r'acqui(?:re|red|sition)|partnership|\bcontract(?:s)?\b|\brevenue\b|licen[cs]e|'
        r'mass production|start of production|\bSOP\b|commercial (?:service|launch|deployment|operation)|'
        r'\bdeployment\b|\bpilot (?:program|service)\b|regulatory approval|\bpermit\b|'
        r'Nissan|Stellantis|Mercedes|Uber|Microsoft|SoftBank|'
        r'투자|유치|기업가치|상장|제휴|협력|양산|상용화|수주|계약|인수',
        re.IGNORECASE),
    # 특정 신호 — 두 중점(사업·상용화 / 연구·기술)을 함께 커버한다. 본문에 있어도 판정.
    focus_specific=re.compile(
        # 사업 · 상용화
        r'funding round|Series [A-E] (?:round|funding)|valuation|\bIPO\b|'
        r'mass production|start of production|\bSOP\b|commercial (?:service|launch|deployment)|'
        r'robotaxi (?:service|trial|launch)|로보택시|양산|상용화|기업가치|'
        # 연구 · 기술
        r'world model|월드 ?모델|end-to-end (?:driving|learning|model)|foundation model|'
        r'\bGAIA-[12]\b|\bLINGO-[12]\b|WayveScenes|LingoQA|\bAV ?2\.0\b|'
        r'benchmark|dataset|데이터셋|논문|preprint|arXiv',
        re.IGNORECASE),
    # 일반 신호 — 제목에 있을 때만 판정 (본문 한 단어 오탐 방지)
    focus_generic=re.compile(
        r'partnership|partners? with|\binvest(?:ments?|s|ed|ing)?\b|\bfunding\b|acqui(?:re|red|sition)|'
        r'\bdeployment\b|launch(?:es|ed)?|expands?|\bcontract(?:s)?\b|joint venture|'
        r'unveils?|introduces?|\bpaper\b|\bmodel\b|research|'
        r'제휴|협력|투자|유치|출시|확장|공개|모델|연구|논문',
        re.IGNORECASE),
    exclude_title=re.compile(
        r'we.?re hiring|now hiring|job opening|인턴 ?모집|채용 ?공고|'
        r'\bdeal\b|deals\b|discount|coupon|% off|특가|할인',
        re.IGNORECASE),
)

PROMPT = Prompt(
    analyst="너는 영국 자율주행 기업 Wayve의 사업·기술 동향 애널리스트다.",
    viewpoint="Wayve",
    scale="""\
9-10: 대규모 투자 유치·기업가치 변동·IPO, OEM 양산(SOP) 계약 확정, 로보택시 상용 서비스 개시, 신규 국가 진출, 기반 모델(GAIA 등) 메이저 세대 공개
7-8: 규모·범위가 명시된 파트너십·라이선스 계약, 주요 연구 성과·논문·데이터셋 공개, 규제 승인·시범 운행 허가, 대형 경쟁사 대비 성능 입증
5-6: 기능 단위 제품 업데이트, 구체성 낮은 제휴, 새 사실이 있는 분석 기사, 기술 블로그
3-4: 해설·의견·후속 보도, 컨퍼런스 발표 예고, 실질 논의가 있는 커뮤니티 글
1-2: 재탕 홍보, Wayve가 지나가듯 언급된 기사
0: Wayve와 무관 (WayV 아이돌 그룹, wavve OTT, 일반적인 'wave' 기사는 0점)""",
    tag_rules="""\
- [릴리스] GitHub: Wayve 저장소는 대부분 논문 코드다. 새 모델·데이터셋 공개면 6점 이상, 의존성 정리·소소한 수정은 2~3점
- [릴리스] arXiv: Wayve 소속 저자의 신규 논문이면 6~8점, 인용만 된 제3자 논문은 1~2점
- [커뮤니티] Hacker News/Reddit: 새 사실이나 현업 반응이 뚜렷할 때만 5점 이상""",
    focus_rule=("[중점 분야] 아래 둘 중 하나에 해당하면 is_focus=true 로 두고 article_type 도 그 토픽으로 고른다.\n"
                "- Business-Deployment: 투자·기업가치, OEM 양산 계약, 로보택시 상용 개시, 신규 지역·고객 확장, 라이선스 계약\n"
                "- Research-Technology: GAIA·LINGO 등 모델 공개, End-to-End 학습·월드 모델 연구, 논문·데이터셋·벤치마크"),
    topic_defs="""\
- Business-Deployment: 투자·기업가치·IPO, OEM 양산 계약, 로보택시 상용 개시, 신규 지역·고객
- Research-Technology: GAIA(월드 모델)·LINGO(설명 가능 주행)·E2E 학습·논문·데이터셋·벤치마크
- Partnership-Ecosystem: 파트너십·투자자·칩/클라우드 공급(NVIDIA, Microsoft 등) 생태계
- Robotaxi-Operations: 로보택시 실제 운행·Uber 제휴 운영·도시 확장·운행 기록
- Product-Platform: AI Driver 제품·ADAS 통합·차량 플랫폼·센서 구성
- Regulation-Policy: 영국·EU·미국·일본 자율주행 규제·승인·법규
- Safety-Assurance: 안전 프레임워크·검증·사고 조사·보험
- Talent-Organization: 채용·조직·경영진 변동
- Competition-Market: 경쟁 구도(Waymo·Tesla·Nuro·Comma 등)·시장 분석
- Community-Signal: 커뮤니티 반응·루머""",
    signal_tags=("funding, valuation, ipo, m&a, partnership, oem-deal, mass-production, robotaxi, deployment, "
                 "regulation, safety, research, model-release, dataset, benchmark, product, hiring, community"),
    angle_desc="Wayve의 사업 포지션·기술 경로에 주는 의미 1~2문장",
    focus_angle_on=("이 항목은 중점 분야(사업·상용화 / 연구·기술) 중 하나다. 사업이면 상용화 단계와 "
                    "고객·지역 범위를, 연구면 기존 접근(규칙 기반·모듈형) 대비 무엇이 달라지는지를 "
                    "focus_angle에 1~2문장으로 반드시 채운다."),
    focus_angle_off="위 두 중점 분야와 직접 관련이 없으면 focus_angle은 빈 문자열로 둔다.",
    top3_rule="중점 분야 항목(표시: [FOCUS])이 있으면 최소 1줄은 그중에서 고르고, 사업과 연구가 모두 있으면 한쪽에 몰지 않는다",
)

SUBJECT = Subject(
    key="wayve",
    slug="wv",
    name="Wayve",
    title="Wayve 사업·기술 동향",
    mail_tag="Wayve 모니터링",
    kicker="WAYVE MONITORING · DAILY",
    accent="#4F46E5",
    accent_dark="#3730A3",
    accent_tint="#EEF2FF",
    focus=(
        Focus("Business-Deployment", "사업·상용화", "📈"),
        Focus("Research-Technology", "연구·기술", "🧠"),
    ),
    focus_short="사업/연구",
    angle_label="Wayve 관점",
    topics=(
        ("Business-Deployment", "사업 · 상용화 (투자 · OEM · 로보택시)"),
        ("Research-Technology", "연구 · 기술 (GAIA · LINGO · E2E)"),
        ("Partnership-Ecosystem", "파트너십 · 생태계"),
        ("Robotaxi-Operations", "로보택시 운영"),
        ("Product-Platform", "제품 · 플랫폼"),
        ("Regulation-Policy", "규제 · 정책"),
        ("Safety-Assurance", "안전 · 검증"),
        ("Talent-Organization", "인재 · 조직"),
        ("Competition-Market", "경쟁 · 시장"),
        ("Community-Signal", "커뮤니티 신호"),
    ),
    keywords=KEYWORDS,
    prompt=PROMPT,
    sources=tuple(SOURCES),
)
