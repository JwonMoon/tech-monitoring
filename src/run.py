#!/usr/bin/env python3
"""기술 모니터링 데일리 파이프라인 엔트리포인트.

  python src/run.py                          # NVIDIA 전체 실행 → out/nvidia/email.html, archive/
  python src/run.py --subject autoware       # Autoware · TIER IV
  python src/run.py --subject autoware --crawl-only   # LLM 없이 소스별 수집·사전필터 현황만
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# config 는 import 시점에 주제를 확정하므로, 패키지보다 먼저 인자를 읽어 환경 변수로 넘긴다.
_ap = argparse.ArgumentParser()
_ap.add_argument("--subject", default=os.environ.get("SUBJECT") or "nvidia",
                 help="모니터링 주제 (nvidia | autoware)")
_ap.add_argument("--crawl-only", action="store_true", help="LLM 없이 수집·사전필터 현황만 출력")
args = _ap.parse_args()
os.environ["SUBJECT"] = args.subject

from techmon import archive, config, crawl, mailer, pipeline, render, state  # noqa: E402


def main():
    t0 = time.time()
    window = sorted(config.TARGET_DATES)
    print(f"{'=' * 60}\n{config.SUBJECT.title} — 대상 {window[0]} ~ {window[-1]} (KST)\n"
          f"backend={config.LLM_BACKEND} · 1차 {config.STAGE1_MODEL} · 2차 {config.STAGE2_MODEL}\n{'=' * 60}")

    print("\n[수집]")
    articles, stats = crawl.crawl_sources()
    seen = state.load()
    unseen = state.filter_unseen(articles, seen)
    print(f"\n수집 {len(articles)}건 → 미발송 {len(unseen)}건 (발송 이력 {len(seen)}건)")
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.crawl_only:
        kept, counts = pipeline.stage0(unseen)
        print(f"\n{'소스':<40}{'피드':>6}{'기간':>6}{'미발송':>7}{'통과':>6}  오류")
        for s in stats:
            c = counts.get(s["source"], [0, 0])
            print(f"{s['source']:<40}{s['raw']:>6}{s['in_window']:>6}{c[0]:>7}{c[1]:>6}  {s['error'][:50]}")
        print(f"\n사전필터 통과 합계: {len(kept)}건")
        failed = [s["source"] for s in stats if s["error"]]
        if failed:
            print(f"수집 실패 {len(failed)}개: {', '.join(failed)}")
        (config.OUT_DIR / "crawl_report.json").write_text(json.dumps(
            {"subject": config.SUBJECT.key, "stats": stats, "stage0": counts,
             "passed": [{k: a[k] for k in ("source", "title", "link", "date")} for a in kept]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    result = pipeline.run(unseen)
    html = render.build_within_limit(result, stats)
    subject = render.subject(result)
    (config.OUT_DIR / "email.html").write_text(html, encoding="utf-8")
    meta = {"subject": subject, "monitor_subject": config.SUBJECT.key,
            "cards": len(result["cards"]), "headlines": len(result["headlines"]),
            "releases": len(result["releases"]), "html_bytes": len(html.encode("utf-8")),
            "failed_sources": [s["source"] for s in stats if s["error"]], "elapsed_min": round((time.time() - t0) / 60, 1)}
    (config.OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    stem = archive.save(config.BASE_DATE, result, stats)
    print(f"\n제목: {subject}\nHTML: {config.OUT_DIR / 'email.html'} ({meta['html_bytes']:,} bytes)\narchive: {stem}.json/.md")

    if config.WRITE_STATE:
        state.mark(seen, result["scored"], config.BASE_DATE)
        print(f"발송 이력 저장: {state.save(seen, config.BASE_DATE)}건")
    if config.MAIL_MODE == "smtp":
        mailer.send(subject, html)
    print(f"완료 ({meta['elapsed_min']}분)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
