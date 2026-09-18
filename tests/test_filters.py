"""Stage 0 사전필터 회귀 확인 — 네트워크·LLM 없이 도는 유일한 테스트.

  python tests/test_filters.py

키워드를 손볼 때마다 여기부터 돌린다. 특히 정규식에 단어 경계 없는 영어 대안을 넣으면
(round → roundup, order → "in order to") 조용히 오탐이 늘어난다.

세 번째 열(focus)은 filters.is_focus — 최종 중점 여부가 아니라 '중점 후보' 키워드 신호다.
최종 중점은 pipeline.adjust 가 LLM 토픽이 Subject.focus_keys 에 드는지로 정한다. 그래서
버려지는(skip/reject) 항목의 focus 값은 의미가 없어 검사하지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from techmon import filters  # noqa: E402
from techmon.subjects import get  # noqa: E402

def art(title, body="", **kw):
    a = {"title": title, "body": body, "prefilter": True, "focus_hint": False}
    a.update(kw); return a

CASES = {
"nvidia": [
    # (제목, 본문, 기대 verdict, 기대 is_focus)
    ("NVIDIA reports record Q3 revenue of $35B", "Colette Kress said data center revenue grew.", "pass", False),
    ("Mercedes-Benz ships DRIVE Thor in 2027 models", "The OEM confirmed start of production.", "pass", True),
    ("Best gaming laptop deals this week", "RTX 4060 laptops are discounted.", "skip", False),
    ("NVIDIA GeForce RTX 5090 deals: lowest price yet", "Discounted at retailers.", "reject", False),
    ("Apple announces new M5 chip", "No mention of the GPU vendor here.", "skip", False),
    ("Some analyst note", "In passing, NVIDIA was mentioned once.", "skip", False),
],
"autoware": [
    ("Autoware 0.52.0 released with new planner", "The Autoware Foundation published autoware_universe 0.52.0.", "pass", False),
    ("TIER IV raises Series F funding to scale robotaxi service", "ティアフォー announced 資金調達 for commercial deployment.", "pass", True),
    ("Equinix opens Tier IV certified data center", "Uptime Institute Tier IV certification for the new data center campus.", "reject", False),
    ("Caterpillar engines meet Tier 4 Final emission rules", "EPA Tier 4 final 배출가스 compliance for off-road engines.", "skip", False),
    ("TIER IV data center hits Uptime Institute grade", "The Tier IV data center campus was certified.", "reject", False),
    ("We're hiring an Autoware perception engineer", "Autoware team job opening, 求人.", "reject", False),
    ("Waymo expands in Phoenix", "No open-source stack named here.", "skip", False),
    ("Random robotics roundup", "One line mentions Autoware in passing.", "skip", False),
    ("How to deploy Autoware on a laptop", "Step by step tutorial.", "pass", False),
    ("Autoware Foundation welcomes 8 new members", "The Autoware Foundation announced new premium members.", "pass", False),
    # TIER IV 회사 동향 — Autoware·자율주행 키워드가 안 붙는 순수 기업 뉴스도 잡혀야 한다
    ("ティアフォーが決算を発表", "株式会社ティアフォーの通期決算。", "pass", True),
    ("ティアフォー、新社長が就任", "ティアフォーの役員人事を発表した。", "pass", True),
    ("TIER IV opens North America subsidiary", "TIER IV, Inc. announced a new subsidiary and hires.", "pass", True),
    ("티어포, 국내 기업과 제휴", "티어포가 협력을 발표했다.", "pass", True),
],
"wayve": [
    # 두 중점(사업·상용화 / 연구·기술)이 모두 잡혀야 한다
    ("Wayve raises $1.2B Series D at $8.6B valuation", "Microsoft, NVIDIA and Uber joined the round.", "pass", True),
    ("Nissan to ship Wayve AI Driver in ProPILOT from FY2027", "Mass production partnership signed.", "pass", True),
    ("Wayve unveils GAIA-2 world model for driving", "The new foundation model improves end-to-end driving.", "pass", True),
    ("Wayve publishes LingoQA dataset", "A benchmark for driving VQA.", "pass", True),
    # 이름 충돌 — 전부 버려져야 한다 ('Wayve' 철자가 아니라서 strong 이 안 걸림)
    ("WayV drops new album teaser", "The K-pop group WayV announced a comeback.", "skip", False),
    ("웨이브, 신규 오리지널 드라마 공개", "OTT 웨이브가 신작을 편성했다.", "skip", False),  # wavve OTT
    ("Riding the wave of AI investment", "Investors are riding a wave of enthusiasm.", "skip", False),  # 일반어 wave
    ("Google Wave shutdown remembered", "The old Google Wave product.", "skip", False),
    # 지나가는 언급 / 채용
    ("Robotaxi roundup for September", "One line mentions Wayve among others.", "skip", False),
    ("We're hiring a Wayve perception engineer", "Wayve job opening.", "reject", False),
]}

fails = 0
for key, cases in CASES.items():
    kw = get(key).keywords
    print(f"\n=== {key} ===")
    for title, body, want_v, want_f in cases:
        a = art(title, body)
        v, why = filters.pre_filter(a, kw)
        f = filters.is_focus(a, kw)
        # 통과한 항목만 중점 신호를 따진다 — 버려진 항목은 파이프라인에 들어가지도 않는다
        ok = v == want_v and (f == want_f if v == "pass" else True)
        fails += not ok
        shown = str(f) if v == "pass" else "-"
        want = want_f if v == "pass" else "-"
        print(f"  {'OK ' if ok else 'FAIL'} {v:<7}(기대 {want_v:<7}) focus={shown:<5}(기대 {want})  {why:<20} | {title[:52]}")

# 공식·공시·릴리스 소스(prefilter=False)는 키워드와 무관하게 통과해야 한다
for key in ("nvidia", "autoware", "wayve"):
    v, _ = filters.pre_filter(art("General Assembly Meeting 2026", prefilter=False), get(key).keywords)
    print(f"공식 소스 우회 ({key}): {v}")
    fails += v != "pass"

print(f"\n{'실패 ' + str(fails) + '건' if fails else '전부 통과'}")
sys.exit(1 if fails else 0)
