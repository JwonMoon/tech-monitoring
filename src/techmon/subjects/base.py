"""모니터링 주제(Subject) 정의 — 주제 추가는 subjects/ 에 파일 하나 + 레지스트리 한 줄.

주제 하나가 소스 목록, Stage 0 키워드, LLM 프롬프트 문구, 토픽 체계, 메일 색/라벨,
아카이브·발송이력 파일 이름(slug)을 모두 들고 있다. 파이프라인 코드는 주제를 모른다.
"""
from dataclasses import dataclass
from typing import Optional, Pattern, Tuple

from ..sources import Source


@dataclass(frozen=True)
class Keywords:
    """Stage 0 사전필터 (정규식, LLM 비용 없음)."""

    strong: Pattern          # 단독으로 이 주제를 가리키는 강한 신호
    business: Pattern        # 사업 신호 (강한 신호가 약할 때 통과 근거)
    focus_specific: Pattern  # 중점 분야 특정 신호 — 본문에 있어도 판정
    focus_generic: Pattern   # 중점 분야 일반어 — 제목에 있을 때만 판정 (본문 한 단어 오탐 방지)
    exclude_title: Pattern   # 제목 기준 제외 (중점 분야 신호가 있으면 예외)
    # 단독으로는 오탐이 잦은 강한 신호(예: "Tier IV"는 데이터센터 등급·배출가스 규제에도 쓰인다).
    # strong 매칭이 전부 ambiguous에서 나왔는데 ambiguous_noise까지 걸리면 다른 주제로 보고 제외한다.
    ambiguous: Optional[Pattern] = None
    ambiguous_noise: Optional[Pattern] = None


@dataclass(frozen=True)
class Prompt:
    """LLM 프롬프트의 주제별 문구. 틀은 prompts.py 가 공유한다."""

    analyst: str        # "너는 ... 애널리스트다." 역할 문장
    viewpoint: str      # "NVIDIA 관점" 처럼 채점 시점의 기준
    scale: str          # 0~10점 기준표
    tag_rules: str      # [릴리스]/[공시]/[커뮤니티] 태그별 규칙
    focus_rule: str     # 중점 분야 판정 규칙 (is_focus / article_type)
    topic_defs: str     # 토픽 정의 목록
    signal_tags: str    # signal_tags 후보
    angle_desc: str     # Stage 2 subject_angle 필드 설명
    focus_angle_on: str
    focus_angle_off: str
    top3_rule: str      # 핵심 3줄 추가 규칙


@dataclass(frozen=True)
class Subject:
    key: str            # CLI/워크플로우에서 쓰는 식별자 (nvidia)
    slug: str           # 파일 이름 접미사 (archive/2026-09-17_nv.json, state/seen_nv.json)
    name: str           # 고유명사 표기 (NVIDIA)
    title: str          # 메일 제목줄·H1
    mail_tag: str       # 메일 제목 대괄호 안 (NVIDIA 모니터링)
    kicker: str         # 메일 헤더 위 작은 글씨

    accent: str
    accent_dark: str
    accent_tint: str

    focus_key: str      # 중점 토픽 키 (항상 첫 섹션 + 가중 + 헤드라인 보존)
    focus_short: str    # 제목줄 표기 (자동차/로봇)
    focus_badge: str    # 카드 안 강조 박스 제목
    focus_empty: str    # 그 섹션이 0건인 날 문구
    angle_label: str    # Stage 2 subject_angle 렌더 라벨 (NVIDIA 관점)

    topics: Tuple[Tuple[str, str], ...]  # (토픽 키, 한국어 라벨) — 순서가 곧 섹션 순서
    keywords: Keywords
    prompt: Prompt
    sources: Tuple[Source, ...]

    hf_watch: Optional[Pattern] = None  # Hugging Face 업데이트(신규 아님)도 실을 모델 이름
    max_cards: int = 15
    max_focus_cards: int = 10
    max_headlines: int = 40

    @property
    def topic_keys(self):
        return [k for k, _ in self.topics]

    @property
    def topic_labels(self):
        return dict(self.topics)

    @property
    def topic_list(self):
        """프롬프트에 넣을 'A | B | C' 문자열."""
        return " | ".join(self.topic_keys)
