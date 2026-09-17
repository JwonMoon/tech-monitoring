"""HTML 메일 렌더 (inline CSS 테이블 레이아웃 — Gmail/Outlook 호환)."""
import html as html_mod
import os
import re

from . import config

S = config.SUBJECT
ACCENT = S.accent
ACCENT_DARK = S.accent_dark
ACCENT_TINT = S.accent_tint
INK = "#111827"
MUTED = "#6B7280"
FAINT = "#9CA3AF"
LINE = "#E5E7EB"
WEEKDAYS = "월화수목금토일"

TOPIC_LABELS = {**S.topic_labels, "기타": "기타"}


def esc(t):
    return html_mod.escape(str(t or ""))


def md_bold(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(t))


def _ok(v):
    return bool(v) and str(v).strip() not in ("미확인", "N/A", "null", "None")


def badge(text, bg, fg):
    return f'<span style="font-size:11px;font-weight:700;padding:1px 7px;border-radius:9px;background:{bg};color:{fg}">{esc(text)}</span>'


def importance_badge(a):
    s = a["score"]
    if s >= 8:
        return badge(f"필독 {s}/10", "#FDE8E8", "#B91C1C")
    if s >= 5:
        return badge(f"주요 {s}/10", ACCENT_TINT, ACCENT_DARK)
    return badge(f"참고 {s}/10", "#F1F5F9", "#64748B")


def title_of(a):
    return (a.get("summary_data") or {}).get("korean_title") or a["stage1"].get("korean_title") or a["title"]


def summary_of(a):
    return (a.get("summary_data") or {}).get("korean_summary") or a["stage1"].get("korean_summary") or ""


def label(text, color=ACCENT_DARK):
    return f'<p style="margin:12px 0 3px;font-size:12px;font-weight:700;color:{color}">{esc(text)}</p>'


def para(text, color="#374151"):
    return f'<p style="margin:0;font-size:13px;line-height:20px;color:{color}">{md_bold(text)}</p>'


def box(inner, bg="#FFFFFF", pad="16px 20px", border=f"1px solid {LINE}", extra=""):
    return (f'<tr><td style="padding:16px 0 0 0;"><table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" border="0" style="border-collapse:separate;"><tr><td style="background-color:{bg};'
            f'border:{border};border-radius:12px;padding:{pad};{extra}">{inner}</td></tr></table></td></tr>')


def section_header(text, sub=""):
    return (f'<tr><td style="padding:26px 2px 0 2px;"><p style="margin:0;font-size:15px;font-weight:700;color:{INK};">'
            f'<span style="display:inline-block;width:8px;height:8px;background-color:{ACCENT};border-radius:2px;'
            f'margin-right:8px;"></span>{esc(text)} <span style="font-weight:400;font-size:12px;color:{FAINT};">'
            f'{esc(sub)}</span></p></td></tr>')


def render_card(a):
    sd = a.get("summary_data") or {}
    parts = []
    act = sd.get("action") or {}
    if _ok(act.get("action")):
        meta = " · ".join(x for x in (act.get("stage"), act.get("timeline")) if _ok(x))
        parts.append(
            f'<div style="margin:12px 0 0 0;padding:12px 14px;background:{ACCENT_TINT};border-left:3px solid {ACCENT};'
            f'border-radius:8px;"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;color:{ACCENT_DARK};">'
            f'핵심 행동{(" · " + esc(meta)) if meta else ""}</p><p style="margin:0;font-size:14px;line-height:22px;'
            f'font-weight:700;color:#0F172A;">{esc(act.get("actor"))}: {md_bold(act.get("action"))}</p>'
            + (f'<p style="margin:4px 0 0 0;font-size:12px;line-height:19px;color:#475569;"><b>범위:</b> {esc(act.get("scope"))}</p>'
               if _ok(act.get("scope")) else "") + "</div>")
    facts = [f for f in (sd.get("key_facts") or []) if _ok(f)]
    if facts:
        lis = "".join(f"<li>{md_bold(f)}</li>" for f in facts[:4])
        parts.append(label("주요 사실") + f'<ul style="margin:0;padding-left:18px;font-size:13px;line-height:20px;color:#374151">{lis}</ul>')
    if _ok(sd.get("why_matters")):
        parts.append(label("왜 중요한가") + para(sd["why_matters"]))
    if _ok(sd.get("subject_angle")):
        parts.append(label(S.angle_label) + para(sd["subject_angle"]))
    if a["is_focus"] and _ok(sd.get("focus_angle")):
        parts.append(
            f'<div style="margin:14px 0 0 0;padding:10px 14px;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;">'
            f'<p style="margin:0 0 3px 0;font-size:11px;font-weight:700;color:#047857;">{esc(S.focus_badge)}</p>'
            f'{para(sd["focus_angle"], "#065F46")}</div>')
    names = [c.get("name") for c in (sd.get("companies") or [])[:4] if isinstance(c, dict)]
    names += [p.get("name") for p in (sd.get("products") or [])[:2] if isinstance(p, dict)]
    names = list(dict.fromkeys(n for n in names if _ok(n)))
    if names:
        parts.append(f'<p style="margin:10px 0 0;font-size:12px;color:{MUTED}"><b>관련</b> {esc(" · ".join(names))}</p>')
    watch = [w for w in (sd.get("watch_next") or []) if _ok(w)]
    if watch:
        parts.append(label("다음 확인 포인트", MUTED) + para(" / ".join(watch[:3]), MUTED))
    if not sd:
        why = "원문 본문을 가져오지 못해 제목·요약만 표시합니다" if a.get("body_missing") else "상세 분석 없음"
        parts.append(para(summary_of(a)) + f'<p style="margin:6px 0 0;font-size:12px;color:{FAINT}">{why} — 원문을 확인하세요.</p>')
    rel = a.get("related") or []
    if rel:
        seen, links = set(), []
        for r in rel:
            if r["link"] in seen:
                continue
            seen.add(r["link"])
            links.append(f'<a href="{esc(r["link"])}" style="color:{ACCENT_DARK};text-decoration:none;">{esc(r["source"])}</a>')
        parts.append(f'<p style="margin:12px 0 0 0;font-size:12px;color:{MUTED};">관련 보도 {len(links)}건: {" · ".join(links[:6])}</p>')
    head = (f'<p style="margin:0 0 8px 0;font-size:11px;color:{MUTED};">{importance_badge(a)}&nbsp;&nbsp;'
            f'<strong>{esc(a["source"])}</strong> · {esc(a["date"])}</p>'
            f'<a name="{a["_anchor"]}" id="{a["_anchor"]}"></a>'
            f'<h2 style="margin:0;font-size:17px;line-height:26px;font-weight:700;"><a href="{esc(a["link"])}" '
            f'style="color:{INK};text-decoration:none;">{esc(title_of(a))}</a></h2>'
            f'<p style="margin:4px 0 0 0;font-size:11px;color:{FAINT};">{esc(a["title"])}</p>')
    foot = (f'<p style="margin:14px 0 0 0;padding-top:10px;border-top:1px solid {ACCENT_TINT};font-size:12px;">'
            f'<a href="{esc(a["link"])}" style="font-weight:700;color:{ACCENT_DARK};text-decoration:none;">원문 보기 →</a>'
            f'&nbsp;&nbsp;<a href="#toc" style="color:{FAINT};text-decoration:none;">↑ 목차</a></p>')
    return box(head + "".join(parts) + foot, pad="18px 22px")


def headline_rows(items):
    rows = "".join(
        f'<tr><td style="padding:9px 0;border-bottom:1px solid #F3F4F6;">'
        f'<p style="margin:0;font-size:13px;line-height:20px;"><a href="{esc(a["link"])}" style="color:{INK};'
        f'font-weight:600;text-decoration:none;">{esc(title_of(a))}</a><span style="color:{FAINT};font-size:11px;">'
        f' · {esc(a["source"])} · {a["score"]}/10</span></p>'
        + (f'<p style="margin:2px 0 0 0;font-size:12px;line-height:18px;color:{MUTED};">{md_bold(summary_of(a))}</p>'
           if summary_of(a) else "") + "</td></tr>"
        for a in items)
    return box(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>',
               pad="4px 20px")


def release_rows(items):
    rows = ""
    for a in items:
        rel = a.get("release") or {}
        rows += (f'<tr><td style="padding:8px 0;border-bottom:1px solid #F3F4F6;">'
                 f'<p style="margin:0;font-size:13px;line-height:20px;">{badge(rel.get("type", "릴리스"), "#F1F5F9", "#475569")}&nbsp; '
                 f'<a href="{esc(a["link"])}" style="color:{INK};font-weight:600;text-decoration:none;">{esc(rel.get("name") or a["title"])}</a>'
                 f'<span style="color:{MUTED};"> {esc(rel.get("version", ""))}</span>'
                 f'<span style="color:{FAINT};font-size:11px;"> · {esc(a["date"][:10])}</span></p>'
                 + (f'<p style="margin:2px 0 0 0;font-size:12px;line-height:18px;color:{MUTED};">{md_bold(summary_of(a))}</p>'
                    if summary_of(a) else "") + "</td></tr>")
    return box(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>',
               pad="4px 20px")


def _bucket(items):
    order = S.topic_keys + ["기타"]
    return [(k, [a for a in items if a["topic"] == k]) for k in order]


def subject(result):
    d = config.BASE_DATE
    day = f"{d.month}/{d.day}({WEEKDAYS[d.weekday()]})"
    cards, heads, rels = result["cards"], result["headlines"], result["releases"]
    total = len(cards) + len(heads) + len(rels)
    if total == 0:
        return f"[{S.mail_tag}] {day} · 신규 0건"
    n_focus = sum(a["is_focus"] for a in cards + heads)
    return (f"[{S.mail_tag}] {day} · {S.focus_short} {n_focus} · 주요 {len(cards)} · "
            f"추가 {len(heads)} · 릴리스 {len(rels)}")


def _page(body_html):
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(S.title)}</title></head>
<body style="margin:0;padding:0;background-color:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Malgun Gothic',Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F3F4F6;">
<tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:860px;color:{INK};">
{body_html}
</table></td></tr></table></body></html>'''


def _run_url():
    if not os.environ.get("GITHUB_RUN_ID"):
        return ""
    return (f'{os.environ.get("GITHUB_SERVER_URL", "https://github.com")}/{os.environ.get("GITHUB_REPOSITORY", "")}'
            f'/actions/runs/{os.environ["GITHUB_RUN_ID"]}')


def build_empty(stats, period):
    """신규 0건인 날의 메일 — 한 줄만.

    파이프라인 생존 확인 때문에 0건이어도 발송은 하되, 읽을 게 없는 날 스크롤할 거리를
    만들지 않는다. 소스별 수집 현황표는 넣지 않고 수집 실패 개수만 남긴다.
    """
    failed = [s["source"] for s in stats if s["error"]]
    url = _run_url()
    foot = f'소스 {len(stats)}개 중 수집 실패 {len(failed)}개' + (f': {esc(", ".join(failed))}' if failed else '')
    return _page(
        f'<tr><td style="background-color:{ACCENT};border-radius:14px;padding:16px 22px;">'
        f'<p style="margin:0 0 3px 0;font-size:11px;font-weight:700;letter-spacing:1px;color:#FFFFFF;opacity:0.85;">{esc(S.kicker)}</p>'
        f'<h1 style="margin:0;font-size:18px;font-weight:800;color:#FFFFFF;">{esc(S.title)}</h1></td></tr>'
        f'<tr><td style="padding:18px 6px 4px 6px;">'
        f'<p style="margin:0 0 4px 0;font-size:15px;font-weight:700;color:{INK};">새로 올라온 소식이 없습니다</p>'
        f'<p style="margin:0;font-size:13px;line-height:20px;color:{MUTED};">{esc(period)} (KST) 기준 · 이미 보낸 항목은 제외했습니다.</p>'
        f'</td></tr>'
        f'<tr><td style="padding:14px 6px 4px 6px;"><p style="margin:0;font-size:11px;line-height:17px;color:{FAINT};">'
        f'{foot}' + (f' · <a href="{esc(url)}" style="color:{FAINT};">실행 로그</a>' if url else '') + '</p></td></tr>')


def build(result, stats):
    cards, heads, rels = result["cards"], result["headlines"], result["releases"]
    for i, a in enumerate(cards):
        a["_anchor"] = f"card{i}"
    window = sorted(config.TARGET_DATES)
    period = f"{window[0]} ~ {window[-1]}" if len(window) > 1 else str(window[0])
    n_focus = sum(a["is_focus"] for a in cards + heads)
    total = len(cards) + len(heads) + len(rels)
    if total == 0:
        return build_empty(stats, period)
    body = []

    body.append(
        f'<tr><td style="background-color:{ACCENT};border-radius:14px;padding:22px 26px;">'
        f'<p style="margin:0 0 4px 0;font-size:12px;font-weight:700;letter-spacing:1px;color:#FFFFFF;opacity:0.85;">{esc(S.kicker)}</p>'
        f'<h1 style="margin:0;font-size:22px;font-weight:800;color:#FFFFFF;">{esc(S.title)}</h1>'
        f'<p style="margin:8px 0 0 0;font-size:12px;color:#FFFFFF;opacity:0.9;">{esc(period)} (KST) · {esc(S.focus_short)} {n_focus} · '
        f'주요 {len(cards)} · 추가 {len(heads)} · 릴리스·공시 {len(rels)}</p></td></tr>')

    if result["top3"]:
        rows = "".join(
            f'<tr><td width="24" valign="top" style="padding:4px 0;"><span style="display:inline-block;width:20px;height:20px;'
            f'line-height:20px;border-radius:10px;background-color:{ACCENT};color:#FFFFFF;font-size:12px;font-weight:700;'
            f'text-align:center;">{i}</span></td><td style="padding:4px 0 4px 8px;font-size:14px;line-height:22px;color:#1F2937;">'
            f'{md_bold(line)}</td></tr>' for i, line in enumerate(result["top3"], 1))
        body.append(box(f'<p style="margin:0 0 8px 0;font-size:13px;font-weight:700;color:{ACCENT_DARK};">오늘의 핵심 3줄</p>'
                        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>'))

    toc = []
    for key, items in _bucket(cards + heads):
        if not items and key != S.focus_key:
            continue
        toc.append(f'<p style="margin:10px 0 4px 0;font-size:12px;font-weight:700;color:{ACCENT_DARK};">'
                   f'{esc(TOPIC_LABELS[key])} <span style="color:{FAINT};font-weight:400;">{len(items)}건</span></p>')
        for a in [x for x in items if x in cards]:
            toc.append(f'<p style="margin:0 0 4px 0;font-size:13px;line-height:20px;">{importance_badge(a)}&nbsp; '
                       f'<a href="#{a["_anchor"]}" style="color:{INK};text-decoration:none;font-weight:600;">{esc(title_of(a))}</a></p>')
    if rels:
        toc.append(f'<p style="margin:10px 0 0 0;font-size:12px;font-weight:700;color:{ACCENT_DARK};">릴리스 · 모델 · 공시 '
                   f'<span style="color:{FAINT};font-weight:400;">{len(rels)}건</span></p>')
    body.append(box('<a name="toc" id="toc"></a>' + f'<p style="margin:0 0 4px 0;font-size:13px;font-weight:700;color:{INK};">목차</p>' + "".join(toc)))

    for key, items in _bucket(cards + heads):
        if not items and key != S.focus_key:
            continue
        body.append(section_header(TOPIC_LABELS[key], f"{len(items)}건"))
        if not items:
            body.append(box(f'<p style="margin:0;font-size:13px;color:{MUTED};">{esc(S.focus_empty)}</p>'))
            continue
        for a in items:
            if a in cards:
                body.append(render_card(a))
        minor = [a for a in items if a not in cards]
        if minor:
            body.append(headline_rows(minor))
    if rels:
        body.append(section_header("릴리스 · 모델 · 공시", f"{len(rels)}건 · GitHub / Hugging Face / SEC"))
        body.append(release_rows(rels))

    failed = [s["source"] for s in stats if s["error"]]
    notices = []
    if result.get("llm_exhausted"):
        notices.append("⚠️ LLM 사용 한도 초과로 일부 항목은 채점·심층 분석 없이 기본 점수로 표시됐습니다.")
    if result.get("omitted"):
        notices.append(f"점수가 낮은 헤드라인 {result['omitted']}건은 메일에서 생략하고 archive에만 기록했습니다.")
    if notices:
        body.append(box("".join(f'<p style="margin:0 0 4px 0;font-size:12px;line-height:19px;color:#92400E;">{esc(n)}</p>'
                                for n in notices), bg="#FFFBEB", border="1px solid #FDE68A"))
    run_url = _run_url()
    body.append(
        f'<tr><td style="padding:26px 2px 8px 2px;"><p style="margin:0;font-size:11px;line-height:18px;color:{FAINT};text-align:center;">'
        f'{esc(S.mail_tag)} · 1차 {esc(config.STAGE1_MODEL)} / 2차 {esc(config.STAGE2_MODEL)} · '
        f'소스 {len(stats)}개 중 수집 실패 {len(failed)}개{(": " + esc(", ".join(failed))) if failed else ""}<br>'
        f'중요도 = LLM 채점(0~10) + 공식 출처 가중 + {esc(S.focus_short)} 가중(+1) · 이미 보낸 항목은 제외'
        + (f'<br><a href="{esc(run_url)}" style="color:{FAINT};">실행 로그</a>' if run_url else "")
        + '</p></td></tr>')

    return _page("".join(body))


def build_within_limit(result, stats):
    """Gmail 클리핑(102KB) 방지. 줄이는 순서:
    1) 일반 헤드라인을 MIN_HEADLINES건까지 저점부터 제거
    2) 저점 카드를 헤드라인으로 강등 (항목 자체는 유지)
    3) 그래도 크면 남은 일반 헤드라인 제거
    중점 분야 헤드라인은 제거하지 않는다."""
    html = build(result, stats)

    def too_big():
        return len(html.encode("utf-8")) > config.MAX_EMAIL_BYTES

    def drop_headline(floor):
        others = [h for h in result["headlines"] if not h["is_focus"]]
        if len(others) <= floor:
            return False
        result["headlines"].remove(min(others, key=lambda a: a["score"]))
        result["omitted"] = result.get("omitted", 0) + 1
        return True

    while too_big() and drop_headline(config.MIN_HEADLINES):
        html = build(result, stats)
    while too_big() and len(result["cards"]) > 1:
        lowest = min(result["cards"], key=lambda a: a["score"])
        result["cards"].remove(lowest)
        result["headlines"].append(lowest)
        result["headlines"].sort(key=lambda a: -a["score"])
        html = build(result, stats)
    while too_big() and drop_headline(0):
        html = build(result, stats)
    return html
