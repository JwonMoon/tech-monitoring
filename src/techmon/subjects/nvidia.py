"""NVIDIA 사업·기술 동향. 중점 분야는 자동차·로봇."""
import re

from ..sources import Source, github_releases, gnews
from .base import Keywords, Prompt, Subject

GITHUB_REPOS = [
    "NVIDIA/TensorRT", "NVIDIA/TensorRT-LLM", "NVIDIA/NeMo", "NVIDIA/Megatron-LM",
    "NVIDIA/cutlass", "NVIDIA/DALI", "NVIDIA/Isaac-GR00T", "isaac-sim/IsaacLab",
    "nvidia-cosmos/cosmos-predict2.5", "triton-inference-server/server", "NVlabs/VILA",
]

SEC_8K = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810"
          "&type=8-K&dateb=&owner=include&count=20&output=atom")

SOURCES = [
    # ── NVIDIA 공식 (1차 출처) ──
    Source("NVIDIA Newsroom", "https://nvidianews.nvidia.com/releases.xml", category="official", weight=1, prefilter=False),
    Source("NVIDIA Blog", "https://blogs.nvidia.com/feed/", category="official", weight=1, prefilter=False),
    Source("NVIDIA Blog · Auto", "https://blogs.nvidia.com/blog/category/auto/feed/", category="official", weight=1, prefilter=False, focus_boost=True),
    Source("NVIDIA Technical Blog", "https://developer.nvidia.com/blog/feed/", category="official", prefilter=False),
    Source("NVIDIA Technical Blog · AV", "https://developer.nvidia.com/blog/category/autonomous-vehicles/feed/", category="official", prefilter=False, focus_boost=True,
           enabled=False, note="2026-09-15 확인 시 엔트리 0건인 빈 피드. 전체 Technical Blog + 자동차 키워드로 커버"),
    Source("NVIDIA Technical Blog · DRIVE", "https://developer.nvidia.com/blog/tag/nvidia-drive/feed/", category="official", prefilter=False, focus_boost=True,
           enabled=False, note="2026-09-15 확인 시 엔트리 0건인 빈 피드"),
    Source("NVIDIA Research", "https://research.nvidia.com/rss.xml", category="official", prefilter=False, enabled=False,
           note="2026-09-15 확인 시 피드에 2021년 글만 있음 (갱신 중단)"),
    Source("YouTube · NVIDIA", "https://www.youtube.com/feeds/videos.xml?channel_id=UCHuiy8bXnmK5nisYHUd1J5g",
           category="official", prefilter=False, fetch_full=False,
           note="2026-09-17 crawl_only 에서 404. 채널 ID 는 맞고(youtube.com/channel/UCHuiy8bXnmK5nisYHUd1J5g) "
                "같은 실행에서 Autoware 채널 피드는 정상이라 이 채널만의 문제. 일단 유지하고 재발하면 비활성"),
    Source("SEC EDGAR 8-K", SEC_8K, kind="sec", category="filing", weight=1, prefilter=False, fetch_full=False, ua="sec"),
    Source("Hugging Face · nvidia", "https://huggingface.co/api/models?author=nvidia&sort=lastModified&limit=100", kind="hf", category="release", prefilter=False, fetch_full=False),
    *github_releases(GITHUB_REPOS),

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
    Source("Google News · NVIDIA", gnews("NVIDIA"), kind="gnews", fetch_full=False),
    Source("Google News · NVIDIA 자동차/로봇",
           gnews('"NVIDIA DRIVE" OR "NVIDIA Isaac" OR Alpamayo OR "DRIVE Thor" OR "Jetson Thor" OR "NVIDIA Cosmos"'),
           kind="gnews", fetch_full=False, focus_boost=True),

    # ── 한국 매체 ──
    Source("디일렉", "https://www.thelec.kr/rss/allArticle.xml", category="kr"),
    Source("전자신문", "https://rss.etnews.com/Section902.xml", category="kr"),
    Source("IT조선", "https://it.chosun.com/rss/allArticle.xml", category="kr"),
    Source("한국경제 IT", "https://www.hankyung.com/feed/it", category="kr", ua="simple", note="전체 Chrome UA는 403, 짧은 UA는 200"),

    # ── 커뮤니티 신호 ──
    Source("Hacker News", "https://hnrss.org/newest?q=nvidia", category="community", weight=-1, fetch_full=False),
    Source("Reddit r/nvidia", "https://www.reddit.com/r/nvidia/new/.rss", category="community", weight=-1, fetch_full=False, ua="bot"),
]

KEYWORDS = Keywords(
    strong=re.compile(
        r'\bNVIDIA\b|엔비디아|\bNVDA\b|Jensen Huang|젠슨 ?황|GeForce|\bRTX ?\d{4}|\bCUDA\b|'
        r'Blackwell|Vera Rubin|\bRubin (?:GPU|CPU|platform|Ultra)|Grace (?:Hopper|Blackwell|CPU)|'
        r'\b(?:H100|H200|H20|B200|B300|GB200|GB300|NVL72|NVL144)\b|\bDGX\b|\bHGX\b|NVLink|NVSwitch|'
        r'Spectrum-X|Quantum-X|Mellanox|Omniverse|Nemotron|TensorRT|\bcuDNN\b|Jetson|'
        r'DRIVE (?:AGX|Thor|Orin|Hyperion|OS|Sim)|Alpamayo|GR00T|Isaac (?:Sim|Lab|ROS)|'
        r'Cosmos (?:Predict|Transfer|Reason)|\bDLSS\b|NVIDIA NIM|Dynamo inference|'
        r'Colette Kress|Ian Buck|Bill Dally|Rev Lebaredian|Deepu Talla|Ali Kani|Jay Puri',
        re.IGNORECASE),
    business=re.compile(
        r'earnings|revenue|guidance|fiscal|quarter|export (?:control|license|ban|rule)|\bBIS\b|'
        r'Commerce Department|tariff|antitrust|\bDOJ\b|\bFTC\b|\bSAMR\b|acqui(?:re|sition)|'
        r'invest(?:ment|s|ed)?|\bstake\b|partnership|\bMOU\b|contract|\bdeal with\b|'
        r'TSMC|CoWoS|\bHBM\b|SK hynix|Samsung|Micron|Foxconn|Wistron|Quanta|Supermicro|'
        r'hyperscaler|CoreWeave|\bxAI\b|OpenAI|sovereign AI|gigawatt|data ?cent(?:er|re)|'
        r'실적|매출|가이던스|수출 ?규제|관세|인수|투자|협력|파트너십|하이닉스|삼성전자|파운드리',
        re.IGNORECASE),
    # 특정 신호: NVIDIA 자동차·로봇 플랫폼명 — 본문에 있어도 판정
    focus_specific=re.compile(
        r'DRIVE (?:AGX|Thor|Orin|Hyperion|OS|Sim)|Alpamayo|\bHyperion\b|Jetson Thor|GR00T|'
        r'Isaac (?:Sim|Lab|ROS|Manipulator|Perceptor)|Cosmos (?:Predict|Transfer|Reason)|NVIDIA Cosmos|'
        r'robotaxi|로보택시|ISO 26262|\bASIL\b',
        re.IGNORECASE),
    # 일반 신호: 로봇·자율주행 일반어, 완성차·AV 기업명 — 제목에 있을 때만 판정
    focus_generic=re.compile(
        r'physical AI|피지컬 ?AI|autonomous (?:driving|vehicle|car|truck|mobile robot)|자율주행|'
        r'self-driving|\bADAS\b|humanoid|휴머노이드|robot|로봇|start of production|'
        r'Mercedes|Toyota|Hyundai|현대차|기아|Volvo|Jaguar Land Rover|\bJLR\b|\bBYD\b|XPeng|\bNIO\b|'
        r'Li Auto|Zeekr|Lucid|Rivian|General Motors|Stellantis|Nissan|Honda|Waymo|Wayve|Nuro|'
        r'Aurora Innovation|Kodiak|Zoox|Pony\.ai|WeRide|Mobileye|Uber (?:AV|autonomous|robotaxi)|'
        r'Figure AI|Agility Robotics|Boston Dynamics|Unitree|Apptronik|Foretellix|Applied Intuition',
        re.IGNORECASE),
    exclude_title=re.compile(
        r'\bdeal\b|deals\b|discount|coupon|% off|\$\d[\d,]* off|price drop|\bsaving\b|save \$|for just \$|lowest price|on sale|'
        r'Black Friday|Prime Day|Cyber Monday|'
        r'giveaway|buying guide|\bbest (?:GPU|graphics card|gaming laptop|laptop)s?\b|'
        r'Game Ready|hotfix driver|\bFPS\b|benchmarked|how to (?:install|overclock|undervolt)|'
        r'특가|할인',
        re.IGNORECASE),
)

PROMPT = Prompt(
    analyst="너는 NVIDIA 사업·기술 동향 애널리스트다.",
    viewpoint="NVIDIA",
    scale="""\
9-10: 분기 실적·가이던스 발표, 수출 규제 결정·라이선스 변화, 10억 달러 이상 M&A·투자, 신규 플래그십 아키텍처/플랫폼 공개·출하, OEM 양산(SOP)·대규모 배치 확정
7-8: 규모·범위가 명시된 대형 파트너십/수주, 주요 SDK·모델 메이저 릴리스, 규제·반독점 조사 진전, 수치가 있는 공급망 뉴스(CoWoS·HBM 물량·가격), 주목할 연구·모델 공개
5-6: 마이너 제품/SDK 기능, 구체성 낮은 파트너십, 새 사실이 있는 분석 기사, 새 기능을 소개하는 기술 블로그
3-4: 해설·의견·후속 보도, 실질 논의가 있는 커뮤니티 글, 주가 등락 기사
1-2: 재탕 홍보, NVIDIA가 지나가듯 언급된 기사, 게이밍 딜·제품 리뷰
0: NVIDIA와 무관""",
    tag_rules="""\
- [릴리스] GitHub/Hugging Face: 메이저 버전·신규 모델·자동차/로봇 관련이면 6점 이상, 패치·버그픽스·소형 파생 모델은 2~4점
- [공시] SEC 8-K: 실적(2.02)·중요계약(1.01)·인수(2.01)는 8점 이상, 임원 변동(5.02) 6~7점, 첨부만(9.01)·기타 4~6점
- [커뮤니티] Hacker News/Reddit: 새 사실이나 개발자 반응이 뚜렷할 때만 5점 이상""",
    focus_rule=("[자동차·로봇] DRIVE(AGX/Thor/Hyperion/OS/Sim), Alpamayo, Cosmos, Isaac, GR00T, Jetson Thor, "
                "자율주행·로보택시·휴머노이드·OEM 협력과 관련되면 is_focus=true, article_type=\"Automotive-Robotics\"."),
    topic_defs="""\
- Automotive-Robotics: 자동차·자율주행·로봇·피지컬 AI
- Business-Finance: 실적·가이던스·주가·투자·M&A·경영진
- Regulation-Policy: 정부 규제·수출통제·반독점·관세·정책 (기술 기사는 여기 넣지 않는다)
- DataCenter-AI: 데이터센터·AI 인프라·클라우드·네트워킹·전력
- GPU-Product: GPU·워크스테이션·PC·칩 제품 출시와 사양
- Software-SDK: CUDA·SDK·라이브러리·소프트웨어 호환성·개발 도구
- Research-Models: 논문·연구·AI 모델 공개
- Supply-Chain: 파운드리·메모리(HBM)·패키징(CoWoS)·조립·공급 물량
- Partnership: 기업 간 협력·고객 사례·생태계
- Community-Signal: 커뮤니티 반응·루머""",
    signal_tags=("earnings, guidance, export-control, regulation, m&a, investment, partnership, new-chip, "
                 "new-platform, sdk-release, model-release, research, supply-chain, automotive, robotics, stock, community"),
    angle_desc="NVIDIA의 사업 포지션·전략에 주는 의미 1~2문장",
    focus_angle_on=("이 항목은 자동차·로봇 관련이다. focus_angle에 자동차·로봇 산업(OEM·자율주행·휴머노이드) "
                    "관점의 의미를 1~2문장으로 반드시 채운다."),
    focus_angle_off="자동차·로봇과 직접 관련이 없으면 focus_angle은 빈 문자열로 둔다.",
    top3_rule="자동차·로봇 항목(표시: [FOCUS])이 있으면 최소 1줄은 그중에서 고른다",
)

SUBJECT = Subject(
    key="nvidia",
    slug="nv",
    name="NVIDIA",
    title="NVIDIA 사업·기술 동향",
    mail_tag="NVIDIA 모니터링",
    kicker="NVIDIA MONITORING · DAILY",
    accent="#76B900",
    accent_dark="#3D6B00",
    accent_tint="#F1F8E6",
    focus_key="Automotive-Robotics",
    focus_short="자동차/로봇",
    focus_badge="🚗 자동차·로봇 관점",
    focus_empty="오늘 자동차·로봇 관련 신규 소식은 없습니다.",
    angle_label="NVIDIA 관점",
    topics=(
        ("Automotive-Robotics", "자동차 · 로봇 (DRIVE · Isaac · Cosmos)"),
        ("Business-Finance", "실적 · 재무 · M&A"),
        ("Regulation-Policy", "규제 · 수출통제 · 정책"),
        ("DataCenter-AI", "데이터센터 · AI 인프라"),
        ("GPU-Product", "GPU · 하드웨어 제품"),
        ("Software-SDK", "소프트웨어 · SDK"),
        ("Research-Models", "연구 · 모델"),
        ("Supply-Chain", "공급망 · 파운드리 · 메모리"),
        ("Partnership", "파트너십 · 생태계"),
        ("Community-Signal", "커뮤니티 신호"),
    ),
    keywords=KEYWORDS,
    prompt=PROMPT,
    sources=tuple(SOURCES),
    hf_watch=re.compile(r"cosmos|alpamayo|gr00t|groot|isaac|drive|nemotron|parakeet|canary|llama-nemotron", re.I),
    max_cards=15,
    max_focus_cards=10,
    max_headlines=40,
)
