"""Stage 0 사전필터 회귀 확인 — 네트워크·LLM 없이 도는 유일한 테스트.

  python tests/test_filters.py

키워드를 손볼 때마다 여기부터 돌린다. 특히 정규식에 단어 경계 없는 영어 대안을 넣으면
(round → roundup, order → "in order to") 조용히 오탐이 늘어난다.
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
]}

fails = 0
for key, cases in CASES.items():
    kw = get(key).keywords
    print(f"\n=== {key} ===")
    for title, body, want_v, want_f in cases:
        a = art(title, body)
        v, why = filters.pre_filter(a, kw)
        f = filters.is_focus(a, kw)
        ok = (v == want_v and f == want_f)
        fails += not ok
        print(f"  {'OK ' if ok else 'FAIL'} {v:<7}(기대 {want_v:<7}) focus={str(f):<5}(기대 {want_f})  {why:<20} | {title[:52]}")

# 공식·공시·릴리스 소스(prefilter=False)는 키워드와 무관하게 통과해야 한다
for key in ("nvidia", "autoware"):
    v, _ = filters.pre_filter(art("General Assembly Meeting 2026", prefilter=False), get(key).keywords)
    print(f"공식 소스 우회 ({key}): {v}")
    fails += v != "pass"

print(f"\n{'실패 ' + str(fails) + '건' if fails else '전부 통과'}")
sys.exit(1 if fails else 0)
