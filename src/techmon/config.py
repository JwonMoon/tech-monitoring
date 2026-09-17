"""환경 변수와 공통 상수. 주제(SUBJECT)는 import 시점에 확정된다."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import subjects

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "archive"


def _int(name, default):
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _bool(name, default=False):
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


# ─── 모니터링 주제 ─────────────────────────────────────
# run.py 가 --subject 를 환경 변수로 옮긴 뒤 이 모듈을 import 한다.
SUBJECT = subjects.get(os.environ.get("SUBJECT"))
STATE_PATH = ROOT / "state" / f"seen_{SUBJECT.slug}.json"
OUT_DIR = Path(os.environ.get("OUT_DIR") or (ROOT / "out" / SUBJECT.key))

# ─── 수집 기간 ─────────────────────────────────────────
# 기본: 오늘(KST) 포함 최근 TARGET_DAYS일. 매일 06시대 실행 기준으로 "어제+오늘"을 보고
# state/seen_*.json 으로 이미 보낸 항목을 걸러 누락·중복을 동시에 막는다.
NOW_KST = datetime.now(KST)
TARGET_DAYS = max(1, _int("TARGET_DAYS", 2))
_target = os.environ.get("TARGET_DATE", "").strip()
BASE_DATE = datetime.strptime(_target, "%Y-%m-%d").date() if _target else NOW_KST.date()
TARGET_DATES = [BASE_DATE - timedelta(days=d) for d in range(TARGET_DAYS)]

# ─── LLM ───────────────────────────────────────────────
LLM_BACKEND = os.environ.get("LLM_BACKEND", "claude").strip().lower()  # claude | exacode
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
TACH_BIN = os.environ.get("TACH_BIN", "tach")
STAGE1_MODEL = os.environ.get("STAGE1_MODEL", "haiku")
STAGE2_MODEL = os.environ.get("STAGE2_MODEL", "sonnet")
LLM_EFFORT = os.environ.get("LLM_EFFORT", "").strip()

# ─── 선별 기준 ─────────────────────────────────────────
# 카드·헤드라인 상한은 주제마다 소스 규모가 달라 주제 기본값을 쓰고, 환경 변수로 덮어쓴다.
MAX_ARTICLES = _int("MAX_ARTICLES", 0)                              # 테스트용 채점 대상 제한 (0=무제한)
MAX_CARDS = _int("MAX_CARDS", SUBJECT.max_cards)                    # 일반 카드 최대
MAX_FOCUS_CARDS = _int("MAX_FOCUS_CARDS", SUBJECT.max_focus_cards)  # 중점 분야 카드 최대 (일반과 별도)
MAX_RELEASES = 25
MIN_HEADLINES = _int("MIN_HEADLINES", 20)  # 메일 크기 가드가 카드보다 먼저 보장하는 헤드라인 수
MAX_HEADLINES = _int("MAX_HEADLINES", SUBJECT.max_headlines)  # 일반 헤드라인 최대 (중점 헤드라인은 별도로 전부 유지)
STAGE1_BATCH_SIZE = 10
MAJOR_SCORE = 5            # 일반 카드 기준
FOCUS_MAJOR_SCORE = 4      # 중점 분야 카드 기준 (가중)
COMMUNITY_MAJOR_SCORE = 7  # 커뮤니티 카드 기준
RELEASE_MAJOR_SCORE = 7    # 릴리스/공시 → 카드 승격 기준
HEADLINE_SCORE = 2         # 헤드라인 최소 점수
SOFT_DEADLINE_MIN = _int("SOFT_DEADLINE_MIN", 45)
# claude CLI 동시 실행 수 (심층 분석이 건당 ~1분이라 순차면 60분 한도를 넘김)
STAGE1_WORKERS = max(1, _int("STAGE1_WORKERS", 3))
STAGE2_WORKERS = max(1, _int("STAGE2_WORKERS", 4))
MAX_EMAIL_BYTES = 95_000   # Gmail 102KB 클리핑 방지

# ─── 실행 모드 ─────────────────────────────────────────
WRITE_STATE = _bool("WRITE_STATE", False)   # CI에서만 1 (로컬 테스트가 발송 이력을 오염시키지 않도록)
IGNORE_SEEN = _bool("IGNORE_SEEN", False)   # 과거 날짜 재실행 시 1
MAIL_MODE = os.environ.get("MAIL_MODE", "file").strip().lower()  # file | smtp

# SEC EDGAR는 연락처가 담긴 User-Agent를 요구한다 (없으면 403). 미설정 시 SEC 소스는 건너뜀.
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "").strip()
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
USER_AGENTS = {
    "browser": BROWSER_UA,
    "simple": "Mozilla/5.0",
    "bot": "tech-monitoring/1.0 (personal news digest)",
    "sec": f"tech-monitoring {CONTACT_EMAIL}",
}

START_TS = datetime.now().timestamp()
