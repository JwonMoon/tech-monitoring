"""수집 — 소스 kind별로 공통 article dict로 정규화."""
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from . import config

_sessions = {}


def _session(ua):
    s = _sessions.get(ua)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = config.USER_AGENTS[ua]
        _sessions[ua] = s
    return s


def http_get(url, ua="browser", timeout=20):
    r = _session(ua).get(url, timeout=timeout)
    r.raise_for_status()
    return r


def parse_dt(value):
    s = (value or "").strip()
    if not s:
        return None
    dt = None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        pass
    if dt is None:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
            if not m:
                return None
            dt = datetime(int(m[1]), int(m[2]), int(m[3]), 12, tzinfo=config.KST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(config.KST)


def in_window(dt):
    return dt is not None and dt.date() in config.TARGET_DATES


def html_to_text(html):
    if not html:
        return ""
    if "<" not in html:
        return re.sub(r"\s+", " ", html).strip()
    return re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ", strip=True)).strip()


_TRACKING = re.compile(r"^(utm_|ref$|ref_|source$|guccounter|mc_|fbclid|gclid|oc$)")


def normalize_url(url):
    if not url:
        return ""
    p = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _TRACKING.match(k)]
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urlencode(q), ""))


def _text(item, *names):
    for n in names:
        t = item.find(n)
        if t is not None and t.get_text(strip=True):
            return t.get_text()
    return ""


def _link(item):
    t = item.find("link", attrs={"rel": "alternate"}) or item.find("link")
    if t is None:
        return ""
    return (t.get("href") or t.get_text(strip=True) or "").strip()


def make_article(src, title, link, dt, body, **extra):
    a = {
        "source": src.name, "source_group": src.name, "category": src.category, "kind": src.kind,
        "weight": src.weight, "prefilter": src.prefilter, "focus_hint": src.focus_boost,
        "title": html_to_text(title), "link": (link or "").strip(),
        "date": dt.strftime("%Y-%m-%d %H:%M") if dt else "", "body": (body or "").strip(),
        "is_release": False, "release": None, "uid": normalize_url(link),
    }
    a.update(extra)
    return a


def _soup(src):
    return BeautifulSoup(http_get(src.url, src.ua).content, "lxml-xml")


def crawl_feed(src):
    soup = _soup(src)
    items = soup.find_all("item") or soup.find_all("entry")
    out = []
    for it in items:
        dt = parse_dt(_text(it, "pubDate", "published", "updated", "dc:date", "date"))
        if not in_window(dt):
            continue
        body = html_to_text(_text(it, "content:encoded", "media:description", "content", "description", "summary"))
        out.append(make_article(src, _text(it, "title"), _link(it), dt, body))
    return len(items), out


def crawl_gnews(src):
    soup = _soup(src)
    items = soup.find_all("item")
    out = []
    for it in items:
        dt = parse_dt(_text(it, "pubDate"))
        if not in_window(dt):
            continue
        title = html_to_text(_text(it, "title"))
        outlet_tag = it.find("source")
        outlet = outlet_tag.get_text(strip=True) if outlet_tag else ""
        if outlet and title.endswith(f" - {outlet}"):
            title = title[: -len(outlet) - 3].strip()
        a = make_article(src, title, _link(it), dt, "", outlet=outlet)
        a["source"] = f"Google News · {outlet}" if outlet else src.name
        out.append(a)
    return len(items), out


SEC_ITEMS = {
    "1.01": "중요 계약 체결", "1.02": "중요 계약 종료", "2.01": "자산 인수·처분 완료",
    "2.02": "실적 발표", "2.03": "직접 채무 발생", "2.05": "구조조정 비용", "3.02": "미등록 증권 매각",
    "5.02": "임원·이사 선임/퇴임/보상", "5.03": "정관 변경", "5.07": "주주총회 결과",
    "7.01": "Reg FD 공개", "8.01": "기타 중요 사건", "9.01": "재무제표·첨부 문서",
}


def crawl_sec(src):
    if not config.CONTACT_EMAIL:
        raise RuntimeError("CONTACT_EMAIL 미설정 — SEC는 연락처 UA 필수라 건너뜀")
    soup = _soup(src)
    entries = soup.find_all("entry")
    out = []
    for e in entries:
        dt = parse_dt(_text(e, "filing-date"))
        if not in_window(dt):
            continue
        codes = re.findall(r"\d\.\d\d", _text(e, "items-desc"))
        desc = ", ".join(f"Item {c} {SEC_ITEMS.get(c, '')}".strip() for c in codes) or "항목 미기재"
        form = _text(e, "filing-type") or "8-K"
        acc = _text(e, "accession-number").strip()
        link = _text(e, "filing-href").strip() or _link(e)
        title = f"{config.SUBJECT.name} SEC {form} 공시 — {desc}"
        body = (f"{config.SUBJECT.name}가 SEC에 {form}({_text(e, 'form-name').strip()})를 제출했다. "
                f"제출일 {_text(e, 'filing-date').strip()}. 공시 항목: {desc}. 원문: {link}")
        out.append(make_article(src, title, link, dt, body, uid=f"sec:{acc}", is_release=True,
                                release={"type": "SEC", "name": form, "version": ", ".join(codes)}))
    return len(entries), out


def crawl_github(src):
    repo = "/".join(urlsplit(src.url).path.strip("/").split("/")[:2])
    soup = _soup(src)
    entries = soup.find_all("entry")
    out = []
    for e in entries:
        dt = parse_dt(_text(e, "updated", "published"))
        if not in_window(dt):
            continue
        link = _link(e)
        tag = link.rsplit("/tag/", 1)[-1] if "/tag/" in link else _text(e, "title")
        title = _text(e, "title").strip()
        a = make_article(src, f"{repo} {title}", link, dt, html_to_text(_text(e, "content"))[:2000],
                         uid=f"gh:{repo}:{tag}", is_release=True,
                         release={"type": "GitHub", "name": repo, "version": tag})
        a["source"] = "GitHub"
        out.append(a)
    return len(entries), out


HF_MAX = 15


def crawl_hf(src):
    models = http_get(src.url, src.ua).json()
    out = []
    for m in models:
        mid = m.get("id") or m.get("modelId") or ""
        created, modified = parse_dt(m.get("createdAt")), parse_dt(m.get("lastModified"))
        is_new = in_window(created)
        watch = config.SUBJECT.hf_watch
        is_update = not is_new and in_window(modified) and bool(watch and watch.search(mid))
        if not (is_new or is_update) or m.get("private"):
            continue
        dt = created if is_new else modified
        tags = [t for t in (m.get("tags") or []) if not t.startswith(("region:", "endpoints", "license:"))][:12]
        body = (f"Hugging Face 모델 {'신규 공개' if is_new else '업데이트'}. pipeline: {m.get('pipeline_tag') or '미기재'} · "
                f"library: {m.get('library_name') or '미기재'} · tags: {', '.join(tags)} · "
                f"downloads {m.get('downloads', 0)} · likes {m.get('likes', 0)}.")
        try:
            readme = http_get(f"https://huggingface.co/{mid}/raw/main/README.md", timeout=10).text
            readme = re.sub(r"^---.*?---", "", readme, flags=re.S)
            body += " README: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)", " ", readme))[:1500]
        except requests.RequestException:
            pass
        label = "신규" if is_new else "업데이트"
        a = make_article(src, f"{mid} ({label})", f"https://huggingface.co/{mid}", dt, body,
                         uid=f"hf:{mid}:{'new' if is_new else dt.date().isoformat()}", is_release=True,
                         release={"type": f"HF·{label}", "name": mid, "version": m.get("pipeline_tag") or ""})
        a["source"] = "Hugging Face"
        out.append(a)
        if len(out) >= HF_MAX:
            break
    return len(models), out


def fetch_full_text(url, timeout=15):
    """원문 페이지 본문 추출 (trafilatura). 실패 시 빈 문자열."""
    try:
        import trafilatura
        html = http_get(url, timeout=timeout).text
        return re.sub(r"\s+", " ", trafilatura.extract(html, include_comments=False) or "").strip()
    except Exception:
        return ""


def resolve_gnews_url(url):
    """Google News 리다이렉트 링크 → (원문 URL 또는 None, 실패 사유)."""
    try:
        from googlenewsdecoder import gnewsdecoder
        res = gnewsdecoder(url, interval=1)
        if res.get("status") and res.get("decoded_url"):
            return res["decoded_url"], ""
        return None, str(res.get("message") or res)[:160]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:140]}"


CRAWLERS = {"feed": crawl_feed, "gnews": crawl_gnews, "sec": crawl_sec, "github": crawl_github, "hf": crawl_hf}


def crawl_sources(sources=None):
    articles, stats = [], []
    for src in (sources or config.SUBJECT.sources):
        if not src.enabled:
            continue
        t0 = time.time()
        try:
            raw, items = CRAWLERS[src.kind](src)
            enriched = 0
            if src.fetch_full:
                for a in items:
                    if len(a["body"]) < 300 and a["link"]:
                        full = fetch_full_text(a["link"])
                        if len(full) > len(a["body"]):
                            a["body"], enriched = full[:6000], enriched + 1
            stats.append({"source": src.name, "raw": raw, "in_window": len(items), "enriched": enriched,
                          "error": "", "sec": round(time.time() - t0, 1)})
            articles.extend(items)
            print(f"  [{src.name}] 피드 {raw}건 → 기간 내 {len(items)}건", flush=True)
        except Exception as e:
            stats.append({"source": src.name, "raw": 0, "in_window": 0, "enriched": 0,
                          "error": str(e)[:160], "sec": round(time.time() - t0, 1)})
            print(f"  [{src.name}] 실패: {str(e)[:160]}", flush=True)
        time.sleep(0.3)
    return articles, stats
