"""LLM 프롬프트 틀. 치환 토큰은 __NAME__ 형식 (JSON 중괄호와 충돌 방지).

주제별 문구(역할·점수표·토픽 정의 등)는 subjects/*.py 의 Prompt 가 채운다.
"""

STAGE1 = """\
__ANALYST__ 아래 항목들을 __VIEWPOINT__ 관점의 중요도로 0~10점 엄격히 채점하라.
순수 JSON 배열만 출력한다. 설명 문장, 코드펜스 금지.

[고유명사] 회사·제품·기술명은 공식 영문 표기를 유지한다 (NVIDIA, Autoware, TIER IV, TSMC, Mercedes-Benz). 한글 음차 금지.

[점수 기준]
__SCALE__

[태그별 규칙]
__TAG_RULES__

__FOCUS_RULE__

[토픽 정의 — 하나만 고른다]
__TOPIC_DEFS__

[출력 형식] 입력 항목마다 객체 하나:
[{"id": 0, "score": 0, "article_type": "토픽 중 하나", "is_focus": false, "signal_tags": ["earnings"], "korean_title": "자연스러운 한국어 제목", "korean_summary": "누가 무엇을 했는지 한국어 한 문장"}]
signal_tags 후보: __SIGNAL_TAGS__

[항목]
__ITEMS__
"""

STAGE2 = """\
다음 항목을 __VIEWPOINT__ 사업·기술 동향 관점에서 심층 분석하라. 순수 JSON 객체만 출력한다.
- 본문에 있는 사실만 쓴다. 없는 일정·수치·의도는 추측하지 말고 "미확인"으로 둔다.
- 고유명사는 공식 영문 표기 유지, 한글 음차 금지.
- 가장 중요한 표현만 **굵게** 표시한다 (key_facts·why_matters·subject_angle·focus_angle에서 필드당 1~2곳).
- __FOCUS_ANGLE_RULE__

{
  "korean_title": "자연스러운 한국어 제목",
  "korean_summary": "누가 + 무엇을 + 왜, 한국어 한 문장",
  "action": {"actor": "주체", "action": "구체적 행동", "stage": "Rumor|Report|Announced|Available|Shipping|Filed|N/A", "timeline": "시점 또는 미확인", "scope": "제품·지역·고객 범위 또는 미확인"},
  "key_facts": ["본문에서 확인된 사실 (수치·날짜 포함), 3~5개"],
  "why_matters": "왜 중요한지 2문장 — 시장·경쟁 구도에서의 의미",
  "subject_angle": "__ANGLE_DESC__",
  "focus_angle": "",
  "companies": [{"name": "기업명", "context": "역할/관계"}],
  "products": [{"name": "제품·플랫폼명", "role": "이 소식에서의 역할"}],
  "watch_next": ["다음에 확인할 것, 최대 3개"]
}

출처: __SOURCE__
제목: __TITLE__
본문:
__BODY__
"""

TOP3 = """\
다음은 오늘 __VIEWPOINT__ 관련 주요 소식 목록이다. 가장 중요한 3가지를 골라 한국어 한 문장씩(90자 이내) 써라.
- 형식: "주체 + 구체적 행동 + 의미"
- __TOP3_RULE__
- 같은 주제 반복 금지, 고유명사 영문 유지, 줄마다 핵심 표현 1곳만 **굵게**
- 입력의 메타데이터(점수, 대괄호 태그)는 출력하지 않는다
순수 JSON만 출력: {"top3": ["...", "...", "..."]}

목록:
__DIGEST__
"""


def _fill(template, subject, **extra):
    p = subject.prompt
    out = (template
           .replace("__ANALYST__", p.analyst)
           .replace("__VIEWPOINT__", p.viewpoint)
           .replace("__SCALE__", p.scale)
           .replace("__TAG_RULES__", p.tag_rules)
           .replace("__FOCUS_RULE__", p.focus_rule)
           .replace("__TOPIC_DEFS__", p.topic_defs)
           .replace("__SIGNAL_TAGS__", p.signal_tags)
           .replace("__ANGLE_DESC__", p.angle_desc)
           .replace("__TOP3_RULE__", p.top3_rule))
    for k, v in extra.items():
        out = out.replace(f"__{k}__", v)
    return out


def stage1(subject, items):
    return _fill(STAGE1, subject, ITEMS=items)


def stage2(subject, source, title, body, focus):
    rule = subject.prompt.focus_angle_on if focus else subject.prompt.focus_angle_off
    return _fill(STAGE2, subject, FOCUS_ANGLE_RULE=rule, SOURCE=source, TITLE=title, BODY=body)


def top3(subject, digest):
    return _fill(TOP3, subject, DIGEST=digest)
