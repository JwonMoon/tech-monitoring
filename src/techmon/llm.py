"""LLM 호출 — claude CLI(기본) 또는 사내 exacode(tach)."""
import json
import re
import subprocess

from . import config

LIMIT_RE = re.compile(r"session limit|usage limit|rate limit|hit your .*limit|overloaded|429", re.I)
STATUS = {"exhausted": False, "reason": ""}

SYSTEM_PROMPT = ("You are a precise analyst that outputs only the JSON requested by the user. "
                 "Never use tools. Never add commentary outside the JSON.")


def call_llm(prompt, model, timeout=300):
    if STATUS["exhausted"]:
        return None
    if config.LLM_BACKEND == "claude":
        # 사용자 환경의 hooks/CLAUDE.md/플러그인이 출력 형식을 바꾸지 않도록 격리
        cmd = [config.CLAUDE_BIN, "-p", "--model", model, "--output-format", "json",
               "--setting-sources", "project", "--system-prompt", SYSTEM_PROMPT,
               "--tools", "", "--no-session-persistence"]
        if config.LLM_EFFORT:
            cmd += ["--effort", config.LLM_EFFORT]
        stdin = prompt
    else:
        cmd = [config.TACH_BIN, "--backend", "exacode", "--raw", prompt]
        stdin = None
    try:
        r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=str(config.ROOT / "src"))
    except subprocess.TimeoutExpired:
        print(f"    [!] LLM 타임아웃 ({timeout}초)", flush=True)
        return None
    except FileNotFoundError:
        print(f"    [!] LLM CLI 없음 (backend={config.LLM_BACKEND})", flush=True)
        return None
    out = (r.stdout or "").strip()
    if config.LLM_BACKEND != "claude":
        return out or None
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        print(f"    [!] claude 출력 해석 실패: {(out or r.stderr)[:300]}", flush=True)
        return None
    if obj.get("is_error"):
        msg = str(obj.get("result"))
        if LIMIT_RE.search(msg) and not STATUS["exhausted"]:
            STATUS.update(exhausted=True, reason=msg[:200])
            print(f"    [!] LLM 사용 한도 초과 — 이후 LLM 호출 중단: {msg[:200]}", flush=True)
        elif not STATUS["exhausted"]:
            print(f"    [!] claude 오류: {msg[:300]}", flush=True)
        return None
    return obj.get("result") or None


def _strip_fence(raw):
    s = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", s)


def parse_json(raw):
    if not raw:
        return None
    try:
        v = json.loads(_strip_fence(raw))
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def parse_json_array(raw):
    if not raw:
        return None
    try:
        v = json.loads(_strip_fence(raw))
        if isinstance(v, list):
            return v
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            v = json.loads(m.group(0))
            return v if isinstance(v, list) else None
        except json.JSONDecodeError:
            pass
    return None
