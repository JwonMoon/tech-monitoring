"""Stage 0 사전필터 (정규식, LLM 비용 없음)."""
import re

# 단독으로 NVIDIA를 가리키는 강한 신호
STRONG_KW = re.compile(
    r'\bNVIDIA\b|엔비디아|\bNVDA\b|Jensen Huang|젠슨 ?황|GeForce|\bRTX ?\d{4}|\bCUDA\b|'
    r'Blackwell|Vera Rubin|\bRubin (?:GPU|CPU|platform|Ultra)|Grace (?:Hopper|Blackwell|CPU)|'
    r'\b(?:H100|H200|H20|B200|B300|GB200|GB300|NVL72|NVL144)\b|\bDGX\b|\bHGX\b|NVLink|NVSwitch|'
    r'Spectrum-X|Quantum-X|Mellanox|Omniverse|Nemotron|TensorRT|\bcuDNN\b|Jetson|'
    r'DRIVE (?:AGX|Thor|Orin|Hyperion|OS|Sim)|Alpamayo|GR00T|Isaac (?:Sim|Lab|ROS)|'
    r'Cosmos (?:Predict|Transfer|Reason)|\bDLSS\b|NVIDIA NIM|Dynamo inference|'
    r'Colette Kress|Ian Buck|Bill Dally|Rev Lebaredian|Deepu Talla|Ali Kani|Jay Puri',
    re.IGNORECASE)

# 사업 신호 (강한 신호와 함께일 때만 통과 근거)
BUSINESS_KW = re.compile(
    r'earnings|revenue|guidance|fiscal|quarter|export (?:control|license|ban|rule)|\bBIS\b|'
    r'Commerce Department|tariff|antitrust|\bDOJ\b|\bFTC\b|\bSAMR\b|acqui(?:re|sition)|'
    r'invest(?:ment|s|ed)?|\bstake\b|partnership|\bMOU\b|contract|\bdeal with\b|'
    r'TSMC|CoWoS|\bHBM\b|SK hynix|Samsung|Micron|Foxconn|Wistron|Quanta|Supermicro|'
    r'hyperscaler|CoreWeave|\bxAI\b|OpenAI|sovereign AI|gigawatt|data ?cent(?:er|re)|'
    r'실적|매출|가이던스|수출 ?규제|관세|인수|투자|협력|파트너십|하이닉스|삼성전자|파운드리',
    re.IGNORECASE)

# 자동차·로봇 신호 (가중 대상)
AUTO_KW = re.compile(
    r'DRIVE (?:AGX|Thor|Orin|Hyperion|OS|Sim)|Alpamayo|Hyperion|Jetson Thor|GR00T|'
    r'Isaac (?:Sim|Lab|ROS|Manipulator|Perceptor)|Cosmos (?:Predict|Transfer|Reason)|NVIDIA Cosmos|'
    r'physical AI|피지컬 ?AI|autonomous (?:driving|vehicle|car|truck|mobile robot)|자율주행|'
    r'self-driving|robotaxi|로보택시|\bADAS\b|humanoid|휴머노이드|robotic|로봇|'
    r'start of production|ISO 26262|\bASIL\b|'
    r'Mercedes|Toyota|Hyundai|현대차|기아|Volvo|Jaguar Land Rover|\bJLR\b|\bBYD\b|XPeng|\bNIO\b|'
    r'Li Auto|Zeekr|Lucid|Rivian|General Motors|Stellantis|Nissan|Honda|Waymo|Wayve|Nuro|'
    r'Aurora Innovation|Kodiak|Zoox|Pony\.ai|WeRide|Mobileye|Uber (?:AV|autonomous|robotaxi)|'
    r'Figure AI|Agility Robotics|Boston Dynamics|Unitree|Apptronik|Foretellix|Applied Intuition',
    re.IGNORECASE)

# 제목 기준 제외 (딜·게이밍 리뷰성). 자동차·로봇 신호가 있으면 예외.
EXCLUDE_TITLE_KW = re.compile(
    r'\bdeal\b|deals\b|discount|coupon|% off|\$\d[\d,]* off|price drop|\bsaving\b|save \$|for just \$|lowest price|on sale|'
    r'Black Friday|Prime Day|Cyber Monday|'
    r'giveaway|buying guide|\bbest (?:GPU|graphics card|gaming laptop|laptop)s?\b|'
    r'Game Ready|hotfix driver|\bFPS\b|benchmarked|how to (?:install|overclock|undervolt)|'
    r'특가|할인',
    re.IGNORECASE)


def is_auto(article):
    if article.get("auto_hint"):
        return True
    return bool(AUTO_KW.search(f"{article['title']} {article['body'][:1500]}"))


def pre_filter(article):
    """('pass'|'skip'|'reject', 이유)"""
    if not article.get("prefilter", True):
        return "pass", "공식·공시·릴리스 소스"
    title = article["title"]
    text = f"{title} {article['body']}"
    strong = STRONG_KW.findall(text)
    if not strong:
        return "skip", "NVIDIA 신호 없음"
    if (not STRONG_KW.search(title) and len(strong) < 2
            and not (BUSINESS_KW.search(text) or AUTO_KW.search(text))):
        return "skip", "지나가는 언급"
    if EXCLUDE_TITLE_KW.search(title) and not AUTO_KW.search(text):
        return "reject", "딜·게이밍 리뷰성"
    return "pass", "NVIDIA 신호"
