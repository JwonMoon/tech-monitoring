"""중점(is_focus) 판정 회귀 — 네트워크·LLM 없이 돈다.

  python tests/test_focus.py

중점은 기본적으로 '토픽이 Subject.focus_keys 에 드는가'로 정하지만, 토픽만 믿으면 LLM 이
토픽을 다르게 고른 순간 가중이 통째로 빠진다. 그래서 LLM 의 is_focus 플래그와 주제 고유
신호(filters.focus_strong)도 중점으로 끌어올린다. 이 파일이 그 계약을 고정한다.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# (제목, 본문, LLM article_type, LLM is_focus, 기대 is_focus, 설명)
CASES = {
    "nvidia": [
        ("NVIDIA DRIVE Thor powers new datacenter workloads", "DRIVE Thor deployment",
         "DataCenter-AI", False, True, "LLM 토픽이 어긋나도 DRIVE Thor 고유 신호로 중점 유지"),
        ("NVIDIA announces new HBM supply deal", "TSMC CoWoS capacity",
         "Supply-Chain", False, False, "자동차 신호 없으면 중점 아님"),
        ("Mercedes ships robotaxi fleet", "robotaxi", "Automotive-Robotics", True, True, "정상 경로"),
    ],
    "autoware": [
        ("Autoware perception model update", "new E2E model", "Perception-AI", False, True, "인지·AI 중점"),
        ("agnocast zero-copy middleware", "middleware", "Architecture-Core", False, True, "아키텍처 중점"),
        ("Autoware docs site refreshed", "documentation only", "Community-Signal", False, False, "중점 아님"),
    ],
    "wayve": [
        ("Wayve GAIA-2 world model", "world model research", "Research-Technology", False, True, "연구 중점"),
        ("Wayve raises Series D", "funding round valuation", "Business-Deployment", False, True, "사업 중점"),
        ("Wayve hires new CFO", "executive appointment", "Talent-Organization", False, False, "인사는 중점 아님"),
    ],
}


def run_one(key):
    """config 가 import 시점에 주제를 확정하므로 주제마다 하위 프로세스로 돈다."""
    from techmon import config, pipeline
    fails = 0
    print(f"\n=== {config.SUBJECT.key} (중점 {len(config.SUBJECT.focus)}개) ===")
    for title, body, at, llm_focus, want, why in CASES[key]:
        a = {"title": title, "body": body, "prefilter": True, "focus_hint": False,
             "weight": 0, "category": "media",
             "stage1": {"parsed": True, "score": 6, "article_type": at, "is_focus": llm_focus,
                        "korean_title": "", "korean_summary": ""}}
        pipeline.adjust([a])
        ok = a["is_focus"] == want
        fails += not ok
        print(f"  {'OK ' if ok else 'FAIL'} focus={str(a['is_focus']):<5}(기대 {want}) "
              f"topic={a['topic']:<22} | {why}")
    return fails


if __name__ == "__main__":
    if os.environ.get("_FOCUS_ONE"):
        sys.exit(1 if run_one(os.environ["_FOCUS_ONE"]) else 0)
    bad = []
    for key in CASES:
        env = {**os.environ, "SUBJECT": key, "_FOCUS_ONE": key}
        if subprocess.run([sys.executable, __file__], env=env).returncode:
            bad.append(key)
    print(f"\n{'실패: ' + ', '.join(bad) if bad else '전부 통과'}")
    sys.exit(1 if bad else 0)
