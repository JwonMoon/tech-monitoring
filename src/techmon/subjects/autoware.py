"""Autoware · TIER IV 사업·기술 동향.

중점 분야는 '사업 · 서비스 배치'. Autoware는 전부가 자율주행이라 NVIDIA처럼 기술 분야로
가중할 게 없다. 대신 놓치기 쉬운 쪽 — 투자·제휴·수주·양산(SOP)·실증·상용 서비스 개시·
인허가 — 을 중점으로 잡아 첫 섹션에 고정하고 가중한다.
"""
import re

from ..sources import Source, github_releases, gnews
from .base import Keywords, Prompt, Subject

# Autoware Foundation 본체 + 참조 구현. 릴리스 Atom 은 태그가 없으면 0건으로 조용히 넘어간다.
AWF_REPOS = [
    "autowarefoundation/autoware",
    "autowarefoundation/autoware_core",
    "autowarefoundation/autoware_universe",
    "autowarefoundation/autoware_launch",
    "autowarefoundation/autoware_msgs",
    "autowarefoundation/AWSIM",
    "autowarefoundation/vision_pilot",
    "autowarefoundation/auto_e2e",
    "autowarefoundation/agnocast",
]
# TIER IV 가 자체 운영하는 주변 스택 (시뮬레이터·센서 드라이버·캘리브레이션·학습·RTOS)
TIER4_REPOS = [
    "tier4/scenario_simulator_v2",
    "tier4/nebula",
    "tier4/CalibrationTools",
    "tier4/AWML",
    "tier4/caret",
    "tier4/awkernel",
]

SOURCES = [
    # ── 공식 (1차 출처) ──
    Source("Autoware Foundation", "https://autoware.org/feed/", category="official", weight=1, prefilter=False),
    Source("TIER IV MEDIA", "https://medium.com/feed/tier-iv-tech-blog", category="official", weight=1, prefilter=False),
    Source("TIER IV 보도자료 (PR TIMES)", "https://prtimes.jp/companyrdf.php?company_id=40119",
           category="official", weight=1, prefilter=False, focus_boost=True,
           note="PR TIMES 기업 RDF. company_id 는 ティアフォー 기업 페이지 기준"),
    Source("YouTube · Autoware Foundation",
           "https://www.youtube.com/feeds/videos.xml?channel_id=UCz-_UeD5shJoQ37LO9Acr1Q",
           category="official", prefilter=False, fetch_full=False),

    # ── 릴리스 ──
    *github_releases(AWF_REPOS),
    *github_releases(TIER4_REPOS),
    Source("Hugging Face · tier4", "https://huggingface.co/api/models?author=tier4&sort=lastModified&limit=50",
           kind="hf", category="release", prefilter=False, fetch_full=False,
           note="모델이 없으면 빈 목록이 와서 0건으로 지나간다"),

    # ── 해외 매체 ──
    Source("The Robot Report", "https://www.therobotreport.com/feed/"),
    Source("IEEE Spectrum · Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss"),
    Source("TechCrunch · transportation", "https://techcrunch.com/category/transportation/feed/"),
    Source("Google News · Autoware", gnews("Autoware"), kind="gnews", fetch_full=False),
    Source("Google News · TIER IV",
           gnews('"TIER IV" OR "Tier IV" autonomous OR Autoware OR robotaxi'),
           kind="gnews", fetch_full=False),
    Source("Google News · Autoware 사업",
           gnews('Autoware OR "TIER IV" funding OR partnership OR "mass production" OR deployment OR robotaxi'),
           kind="gnews", fetch_full=False, focus_boost=True),
    # ── TIER IV 회사 동향 ──
    # 위 질의는 Autoware·자율주행 기술 문맥에 걸린 것만 잡는다. 자금조달·상장·결산·인사·자회사처럼
    # 기술 키워드가 안 붙는 순수 기업 뉴스는 아래 두 질의로 따로 훑는다.
    Source("Google News · TIER IV 기업 (JP)",
           gnews("ティアフォー 資金調達 OR 上場 OR 決算 OR 買収 OR 提携 OR 人事 OR 子会社", lang="ja", gl="JP"),
           kind="gnews", fetch_full=False, focus_boost=True),
    Source("Google News · TIER IV corporate",
           gnews('"TIER IV" Japan funding OR IPO OR revenue OR acquisition OR partnership OR hires OR "North America"'),
           kind="gnews", fetch_full=False, focus_boost=True),

    # ── 일본 매체 (TIER IV 본사·주요 실증 지역) ──
    Source("Google News · ティアフォー (JP)", gnews("ティアフォー OR Autoware OR 自動運転レベル4", lang="ja", gl="JP"),
           kind="gnews", fetch_full=False),
    Source("レスポンス (response.jp)", "https://response.jp/rss/index.rdf", category="media",
           note="자동차 전문. Autoware·ティアフォー 키워드가 있을 때만 통과"),

    # ── 한국 매체 ──
    Source("Google News · 자율주행 오픈소스 (KR)", gnews("Autoware OR 오토웨어 OR 티어포", lang="ko", gl="KR"),
           kind="gnews", category="kr", fetch_full=False),
    Source("디일렉", "https://www.thelec.kr/rss/allArticle.xml", category="kr"),
    Source("전자신문", "https://rss.etnews.com/Section902.xml", category="kr"),

    # ── 커뮤니티 신호 ──
    # ROS Discourse Autoware 카테고리는 AWF 릴리스·WG 공지가 올라오는 곳이라 일반 커뮤니티보다 신호가 좋다.
    Source("ROS Discourse · Autoware", "https://discourse.ros.org/c/autoware/46.rss",
           category="community", weight=0, prefilter=False, fetch_full=False),
    Source("Hacker News", "https://hnrss.org/newest?q=autoware", category="community", weight=-1, fetch_full=False),
    Source("Reddit r/SelfDrivingCars", "https://www.reddit.com/r/SelfDrivingCars/new/.rss",
           category="community", weight=-1, fetch_full=False, ua="bot"),
]

KEYWORDS = Keywords(
    strong=re.compile(
        r'\bAutoware\b|오토웨어|オートウェア|\bAWSIM\b|\bAWML\b|Open ?AD ?Kit|'
        r'Pilot\.Auto|Web\.Auto|autoware[_.](?:universe|core|launch|msgs|tools)|'
        r'scenario_simulator|agnocast|awkernel|safe_drive|\bCARET\b|'
        r'TIER ?IV|TIER ?4, ?Inc|ティアフォー|티어포|Shinpei Kato|加藤真平',
        re.IGNORECASE),
    # "Tier IV" 는 데이터센터 등급(Uptime Institute)·배출가스 규제(Tier 4 Final)에도 쓰인다.
    # 강한 신호가 이것뿐인데 아래 잡음까지 걸리면 다른 주제로 보고 제외한다.
    ambiguous=re.compile(r'TIER ?IV|TIER ?4', re.IGNORECASE),
    ambiguous_noise=re.compile(
        r'Uptime Institute|data ?cent(?:er|re) tier|tier ?(?:iv|4) data ?cent|데이터센터 등급|'
        r'Tier ?4 (?:Final|final|engine|diesel|emission)|배출가스|비도로용|EPA Tier',
        re.IGNORECASE),
    business=re.compile(
        r'\bfunding\b|Series [A-F]\b|funding round|valuation|\bIPO\b|\binvest(?:ments?|s|ed|ing)?\b|'
        r'\bstake\b|acqui(?:re|red|sition)|partnership|\bMOU\b|joint development|\bcontract(?:s)?\b|'
        r'purchase order|\brevenue\b|\bearnings\b|mass production|start of production|\bSOP\b|'
        r'commercial (?:service|launch|deployment|operation)|pilot (?:program|service)|\bdeployment\b|'
        r'\bsubsidy\b|certification|regulatory approval|operating permit|'
        # TIER IV 기업 동향 — 기술 키워드가 안 붙는 순수 회사 뉴스 (결산·인사·조직)
        r'資金調達|上場|出資|提携|協業|共同開発|量産|実証(?:実験)?|商用化|受注|認可|許可|補助金|'
        r'決算|買収|増資|子会社|役員|新社長|就任|採用強化|'
        r'투자|유치|상장|제휴|협력|공동 ?개발|양산|실증|상용화|수주|인가|허가|보조금|'
        r'결산|인수|증자|자회사|대표이사|선임',
        re.IGNORECASE),
    # 특정 신호: 사업화·배치 단계를 가리키는 구체 표현 — 본문에 있어도 판정
    focus_specific=re.compile(
        r'robotaxi|로보택시|ロボタクシー|robo-?bus|自動運転バス|자율주행 ?버스|'
        r'\bLevel ?4\b|レベル4|레벨 ?4|\bODD\b|remote (?:monitoring|operation)|遠隔監視|'
        r'mass production|start of production|\bSOP\b|commercial (?:service|launch|deployment)|'
        r'資金調達|上場|実証実験|商用運行|量産|양산|상용 ?운행|실증 ?사업|買収|決算|'
        r'Series [A-F] (?:round|funding)|\bIPO\b',
        re.IGNORECASE),
    # 일반 신호: 제목에 있을 때만 판정 (본문 한 단어 오탐 방지)
    focus_generic=re.compile(
        r'partnership|partners? with|\binvest(?:ments?|s|ed|ing)?\b|\bfunding\b|acqui(?:re|red|sition)|'
        r'\bdeployment\b|launch(?:es|ed)?|\bcontract(?:s)?\b|\bcustomers?\b|joint venture|'
        # 기업 동향 — 자회사·임원 인사도 TIER IV 회사 소식이라 중점 섹션으로 올린다.
        # 이 정규식은 제목에만, 그것도 이미 주제 신호가 잡힌 기사에만 적용돼 오탐 여지가 좁다.
        r'subsidiar(?:y|ies)|\bhires\b|appoints?|'
        r'提携|協業|導入|開始|受注|出資|子会社|新社長|就任|役員|人事|'
        r'제휴|협력|도입|공급|수주|출시|투자|계약|자회사|대표이사|선임',
        re.IGNORECASE),
    exclude_title=re.compile(
        r'we.?re hiring|now hiring|job opening|採用情報|求人|인턴 ?모집|채용 ?공고|'
        r'\bdeal\b|deals\b|discount|coupon|% off|특가|할인',
        re.IGNORECASE),
)

PROMPT = Prompt(
    analyst="너는 오픈소스 자율주행 스택 Autoware와 이를 주도하는 TIER IV(ティアフォー)의 사업·기술 동향 애널리스트다.",
    viewpoint="Autoware · TIER IV",
    scale="""\
9-10: TIER IV 대규모 투자 유치·상장·M&A, OEM 양산(SOP) 확정, 레벨4 상용 서비스 개시·인가, Autoware 메이저 아키텍처 전환(Core/Universe 구조 변경, ROS 2 배포 이관)
7-8: 규모·범위가 명시된 대형 제휴·수주, Autoware 마이너 버전 릴리스와 주요 기능 추가, 대형 실증 사업 착수, Autoware Foundation 거버넌스·프리미엄 멤버 변동, 안전 표준·인증 진전
5-6: 신규 패키지·툴 공개, 구체성 낮은 제휴, 새 사실이 있는 기술 블로그·분석 기사, 워킹그룹 로드맵 공유
3-4: 해설·의견·후속 보도, 컨퍼런스 발표 예고, 실질 논의가 있는 커뮤니티 글
1-2: 재탕 홍보, Autoware/TIER IV가 지나가듯 언급된 기사, 개인 튜토리얼·설치 후기
0: Autoware·TIER IV와 무관 (데이터센터 Tier IV 등급, 배출가스 Tier 4 규제는 0점)""",
    tag_rules="""\
- [릴리스] GitHub: autoware / autoware_core / autoware_universe 의 마이너 이상 버전은 6점 이상, 패치·의존성 범프·자동 생성 릴리스는 2~4점
- [릴리스] 주변 저장소(AWSIM, scenario_simulator_v2, nebula, AWML 등)는 새 기능·센서 지원 추가일 때만 5점 이상
- [커뮤니티] ROS Discourse: AWF 공식 공지·릴리스 노트·워킹그룹 회의록은 5~7점, 개별 질문·트러블슈팅은 1~2점""",
    focus_rule=("[사업·서비스 배치] 투자·상장·M&A, 제휴·수주·공동개발, 양산(SOP)·상용 서비스 개시, 실증 사업, "
                "인허가·보조금, 신규 고객·지역 확대와 관련되면 is_focus=true, article_type=\"Business-Deployment\"."),
    topic_defs="""\
- Business-Deployment: 투자·상장·제휴·수주·양산·상용 서비스·실증·인허가
- Foundation-Governance: Autoware Foundation 멤버십·거버넌스·총회·행사(ROSCon, AWF GA)
- Release-Version: Autoware 릴리스·버전·ROS 2 배포 대응·마이그레이션
- Architecture-Core: 아키텍처, Core/Universe 구조, 미들웨어·실시간성(agnocast, awkernel, CARET)
- Perception-AI: 인지·인식·예측·End-to-End 모델·데이터셋·학습
- Planning-Control: 경로 계획·행동 결정·제어·차량 인터페이스
- Simulation-Tools: 시뮬레이터·시나리오·캘리브레이션·개발 도구(AWSIM, scenario_simulator_v2)
- Safety-Standard: 기능안전·ODD·법규·표준·인증·사고 조사
- Ecosystem-Hardware: 센서·ECU·컴퓨팅 플랫폼·반도체 파트너(NVIDIA, Arm, Renesas 등)·차량 플랫폼
- Community-Signal: 커뮤니티 반응·질문·루머""",
    signal_tags=("funding, ipo, m&a, partnership, order, mass-production, deployment, pilot, regulation, "
                 "certification, release, architecture, perception, planning, simulation, safety, hardware, "
                 "foundation, community"),
    angle_desc="Autoware 생태계와 TIER IV의 사업 포지션·전략에 주는 의미 1~2문장",
    focus_angle_on=("이 항목은 사업·서비스 배치 관련이다. focus_angle에 상용화 단계(실증 → 양산 → 서비스), "
                    "고객·지역 범위, 경쟁 구도 관점의 의미를 1~2문장으로 반드시 채운다."),
    focus_angle_off="사업·서비스 배치와 직접 관련이 없으면 focus_angle은 빈 문자열로 둔다.",
    top3_rule="사업·서비스 배치 항목(표시: [FOCUS])이 있으면 최소 1줄은 그중에서 고른다",
)

SUBJECT = Subject(
    key="autoware",
    slug="aw",
    name="Autoware · TIER IV",
    title="Autoware · TIER IV 사업·기술 동향",
    mail_tag="Autoware 모니터링",
    kicker="AUTOWARE · TIER IV MONITORING · DAILY",
    accent="#0E7490",
    accent_dark="#155E75",
    accent_tint="#ECFEFF",
    focus_key="Business-Deployment",
    focus_short="사업/배치",
    focus_badge="📈 사업 · 서비스 배치 관점",
    focus_empty="오늘 사업·서비스 배치 관련 신규 소식은 없습니다.",
    angle_label="Autoware · TIER IV 관점",
    topics=(
        ("Business-Deployment", "사업 · 서비스 배치 (투자 · 제휴 · 양산 · 실증)"),
        ("Foundation-Governance", "Autoware Foundation · 거버넌스"),
        ("Release-Version", "릴리스 · 버전"),
        ("Architecture-Core", "아키텍처 · 코어 · 미들웨어"),
        ("Perception-AI", "인지 · AI 모델"),
        ("Planning-Control", "계획 · 제어"),
        ("Simulation-Tools", "시뮬레이션 · 개발 도구"),
        ("Safety-Standard", "안전 · 법규 · 표준"),
        ("Ecosystem-Hardware", "생태계 · 하드웨어 파트너"),
        ("Community-Signal", "커뮤니티 신호"),
    ),
    keywords=KEYWORDS,
    prompt=PROMPT,
    sources=tuple(SOURCES),
    hf_watch=re.compile(r"awml|autoware|tier4|bevfusion|centerpoint", re.I),
    # 소스가 NVIDIA보다 적고 Claude 구독 한도를 둘이 나눠 쓰므로 상한을 낮게 잡는다.
    max_cards=10,
    max_focus_cards=8,
    max_headlines=30,
)
