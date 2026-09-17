"""주제 레지스트리. 주제 추가 = subjects/<key>.py 한 파일 + 아래 한 줄."""
from . import autoware, nvidia

SUBJECTS = {s.key: s for s in (nvidia.SUBJECT, autoware.SUBJECT)}
DEFAULT = nvidia.SUBJECT.key


def get(key):
    key = (key or DEFAULT).strip().lower()
    if key not in SUBJECTS:
        raise SystemExit(f"알 수 없는 주제: {key!r} (가능: {', '.join(SUBJECTS)})")
    return SUBJECTS[key]
