# 기술 모니터링 파이프라인 설계

> 2026-09-15 기준, 2026-09-17 다주제로 확장.
> 사내 `ad-newsletter`의 데일리 뉴스 파이프라인(`ad_news_exa.py`) 구조에서 출발했다.

## 목표와 원칙

- 한 주제의 사업(실적·투자·규제·공급망·파트너십)과 기술(제품·SDK·모델·연구)을 빠짐없이 모니터링
- 주제마다 **중점 분야**를 하나 정해 가중 + 첫 섹션 고정 + 헤드라인 이하로 탈락하지 않음
- 공식 1차 출처(보도자료·공시·GitHub·HF)를 매체 보도보다 우선
- 같은 소식은 한 번만, 여러 매체 보도는 "관련 보도"로 묶음
- 매일 발송, 0건인 날도 알림 (파이프라인 생존 확인)
- **파이프라인 코드는 주제를 모른다.** 주제는 데이터다

## 주제 추상화 (`subjects/`)

주제 하나 = `subjects/<key>.py` 파일 하나 + `subjects/__init__.py` 한 줄. 파일이 드는 것:

| 필드 | 쓰이는 곳 |
|---|---|
| `key` / `slug` | CLI·워크플로우 식별자 / `archive/YYYY-MM-DD_<slug>.json`, `state/seen_<slug>.json` |
| `sources` | `crawl.crawl_sources()` |
| `keywords` (`Keywords`) | `filters.pre_filter()`, `filters.is_focus()` |
| `prompt` (`Prompt`) | `prompts.stage1/stage2/top3()` 가 공용 틀에 끼워 넣는 문구 |
| `topics` | 섹션 순서와 한국어 라벨, Stage 1 `article_type` 후보 |
| `focus_key` 외 focus_* | 중점 분야 토픽 키, 제목줄 표기, 카드 배지, 0건 안내 문구 |
| `accent` 3색, `title`, `kicker`, `mail_tag` | 메일 렌더 — 주제별로 색이 달라야 받은편지함에서 구분된다 |
| `max_cards` / `max_focus_cards` / `max_headlines` | 주제별 기본 상한 (환경 변수로 덮어쓰기 가능) |

`config.SUBJECT`가 import 시점에 `SUBJECT` 환경 변수로 확정된다. `run.py`가 `--subject`를
argparse로 받아 환경 변수에 넣은 뒤 패키지를 import 한다.

### 현재 주제

| 주제 | 중점 분야 | 근거 |
|---|---|---|
| `nvidia` | 자동차 · 로봇 | 전 분야를 보되 DRIVE·Isaac·Cosmos·OEM 협력을 먼저 본다 |
| `autoware` | 사업 · 서비스 배치 | Autoware는 전부가 자율주행이라 기술 분야로 가중할 게 없다. 대신 놓치기 쉬운 투자·제휴·수주·양산(SOP)·실증·인허가를 중점으로 잡는다 |

## 수집 기간과 중복 방지

- 기간: 기준일(KST) 포함 최근 `TARGET_DAYS`(기본 2)일
- 06:17 KST 실행 시 "어제만" 보면 전날 06:17 이후 발행분 중 일부를 영구 누락할 수 있어 2일 창을 쓴다
- 겹치는 하루는 `state/seen_<slug>.json`으로 제거 (주제별로 따로). 채점된 항목의 uid(병합된 관련 보도 포함)를 기록하고 30일 뒤 삭제
- uid: 추적 파라미터를 뺀 정규화 URL, GitHub는 `gh:저장소:태그`, HF는 `hf:모델:new|날짜`, SEC는 `sec:접수번호`
- 로컬 실행은 기본적으로 이력을 쓰지 않는다 (`WRITE_STATE=0`)

## 소스 kind별 정규화 (`crawl.py`)

| kind | 처리 |
|---|---|
| feed | RSS `item` / Atom `entry` 공통 파싱. 본문 300자 미만이면 trafilatura로 원문 보강 (`fetch_full=True` 소스만) |
| gnews | 제목 끝 ` - 매체명` 분리, 출처를 `Google News · 매체명`으로 표기. 본문 없음 → 카드 승격 시에만 `googlenewsdecoder`로 원문 URL 복원 후 추출 |
| sec | 8-K Atom의 `filing-date`, `items-desc`, `accession-number` 사용. Item 코드를 한국어 설명으로 변환 (2.02=실적, 1.01=중요 계약, 5.02=임원 등). User-Agent에 연락처 필수 |
| github | 릴리스 Atom. 태그와 릴리스 노트 2,000자 |
| hf | 모델 목록 API. `createdAt`이 기간 내면 신규, `lastModified`만 바뀐 건 주제별 워치리스트(`Subject.hf_watch`)에 걸릴 때만 업데이트로 포함. 하루 최대 15건, README 1,500자 |

## Stage 0 사전필터 (`filters.py`)

`filters`는 정규식을 들고 있지 않다. 주제의 `Keywords`를 인자로 받는 순수 함수다.

- 공식·공시·릴리스 소스(`prefilter=False`)는 무조건 통과
- 매체·커뮤니티: `strong`(주제명·제품·플랫폼·인물) 필수
  - 제목에 없고 본문에 1회뿐이면 `business` 또는 `focus_specific`(본문) / `focus_generic`(제목) 동반 필요
- 제목에 딜·홍보성 표현(`exclude_title`)이 있으면 제외 (중점 분야 신호가 있으면 예외)
- 주가 기사는 제외하지 않음 → 채점 3~4점 헤드라인

### 동음이의 가드 (`ambiguous` / `ambiguous_noise`)

"Tier IV"는 데이터센터 등급(Uptime Institute)과 배출가스 규제(Tier 4 Final)에도 쓰인다.
강한 신호가 **전부** `ambiguous`에서만 나왔는데 `ambiguous_noise`(데이터센터·배출가스 문맥)까지
걸리면 다른 주제의 기사로 보고 `reject`한다. NVIDIA는 둘 다 `None`이라 이 경로를 타지 않는다.

### 키워드를 고칠 때

정규식에 단어 경계 없는 영어 대안을 넣으면 조용히 오탐이 는다 (`round` → "roundup",
`order` → "in order to", `permit` → "is not permitted", `invest` → "investigation").
`tests/test_filters.py`가 이 종류를 잡는다. 네트워크·LLM 없이 1초에 돌고 CI에서도 매 실행 전에 돈다.

## Stage 1 채점 기준 (`prompts.STAGE1`)

점수표·태그 규칙·토픽 정의는 주제의 `Prompt`가 채운다. 아래는 NVIDIA 기준이고,
Autoware는 같은 자리에 "TIER IV 투자·상장, OEM 양산 확정, 레벨4 상용 인가"가 9-10점으로 들어간다.

| 점수 | 기준 |
|---|---|
| 9-10 | 분기 실적·가이던스, 수출 규제 결정, 10억 달러 이상 M&A·투자, 플래그십 아키텍처 공개·출하, OEM 양산 확정 |
| 7-8 | 범위가 명시된 대형 파트너십, 주요 SDK·모델 메이저 릴리스, 규제 조사 진전, 수치 있는 공급망 뉴스 |
| 5-6 | 마이너 제품·SDK 기능, 구체성 낮은 파트너십, 새 사실이 있는 분석 기사, 기술 블로그 |
| 3-4 | 해설·후속 보도, 커뮤니티 논의, 주가 등락 |
| 1-2 | 재탕 홍보, 지나가는 언급, 딜·리뷰 |
| 0 | 무관 |

태그별: `[릴리스]` 메이저 6+ / 패치 2~4, `[공시]` 2.02·1.01·2.01은 8+ / 5.02는 6~7.
파싱 실패 시 기본 점수: 공식·공시 4, 릴리스 3, 그 외 2 (누락 방지).

## 가중과 분류 (`pipeline.adjust`, `classify`)

- 최종 점수 = LLM 점수 + 소스 가중(공식·공시 +1, 지정 매체 +1, 커뮤니티 -1) + 중점 분야 +1
- 중점 분야 판정 = LLM `is_focus` OR `focus_specific`(제목+본문 앞부분) OR `focus_generic`(제목) OR 중점 전용 피드(`focus_boost`)
- 중점 분야 항목은 최소 헤드라인 점수 보장
- 카드 기준: 일반 5, 중점 4, 커뮤니티 7, 릴리스·공시 7 (미만은 보드)
- 카드 상한: 주제별 (`max_cards` / `max_focus_cards` — NVIDIA 15/10, Autoware 10/8). 넘치면 헤드라인으로
- 헤드라인 상한: 주제별 (NVIDIA 40, Autoware 30. 중점 분야 헤드라인은 전부 유지). 넘친 저점 항목은 archive에만 기록
- 메일 HTML이 95KB를 넘으면: 일반 헤드라인을 20건까지 저점부터 제거 → 저점 카드를 헤드라인으로 강등 → 남은 일반 헤드라인 제거 (Gmail 102KB 클리핑). 중점 분야 헤드라인은 제거하지 않음

## 병합 (`merge_duplicates`)

1. Stage 1 전: uid 동일 또는 제목 유사도(SequenceMatcher) 0.85 이상
2. Stage 1 후: 한국어 제목 유사도 0.8 이상 + 같은 토픽 (영문·한글 보도 중복)
- 대표 우선순위: 공식 > 공시 > 릴리스 > 해외 매체 > 국내 매체 > Google News > 커뮤니티
- 릴리스 항목과 15자 미만 제목은 유사도 병합 대상에서 제외

## Stage 2 심층 분석 (`prompts.STAGE2`)

카드마다 JSON: `action{actor, action, stage, timeline, scope}`, `key_facts`, `why_matters`, `subject_angle`(주제 관점), `focus_angle`(중점 분야만), `companies`, `products`, `watch_next`.
본문에 없는 내용은 "미확인" — 렌더 시 숨김.

본문 확보: Google News 카드는 `googlenewsdecoder`로 원문 URL 복원 → 실패하면 병합된 관련 보도 중 Google News가 아닌 링크에서 추출.
모두 실패하면 LLM 분석 없이 1차 요약만 담은 카드로 유지하고 "원문 본문을 가져오지 못해" 문구를 표시한다 (중요 소식 누락 방지).

## 실행 시간과 LLM 예산

2026-09-15 측정(NVIDIA): 전 소스 수집 약 1.5분, 원시 307건 → 사전필터 158건 → 병합 133건.
심층 분석은 sonnet 기준 건당 약 1분이라 `STAGE2_WORKERS=4`로 병렬 처리.
`SOFT_DEADLINE_MIN=45`를 넘기면 남은 카드는 분석 없이 헤드라인으로 내려 60분 잡 제한 안에서 끝낸다.

주제가 둘이 되면서 **하나의 Claude 구독 한도를 나눠 쓴다.** 그래서
(1) 주제별 잡을 `max-parallel: 1`로 순차 실행하고,
(2) Autoware 상한을 NVIDIA보다 낮게(카드 10/8, 헤드라인 30) 잡았다.
한도를 소진하면 `llm.STATUS["exhausted"]`가 켜져 그 주제의 이후 호출이 즉시 중단되고
메일에 안내 문구가 붙는다. 다음 주제 잡은 별도 프로세스라 다시 시도한다.

소스를 점검할 때는 `crawl_only` 입력으로 실행한다. Claude 설치·인증·호출을 전부 건너뛰므로
**LLM 사용량이 0이다.**

## 소스 점검 기록

| 날짜 | 소스 | 상태 | 조치 |
|---|---|---|---|
| 2026-09-15 | NVIDIA Research RSS | 2021년 글만 남음 | 비활성 |
| 2026-09-15 | Technical Blog AV·DRIVE 카테고리 피드 | 엔트리 0건 | 비활성 (전체 Technical Blog + 자동차 키워드로 커버) |
| 2026-09-15 | 한국경제 IT | 전체 Chrome UA는 403 | 짧은 UA(`simple`) 사용 |
| 2026-09-15 | SEC EDGAR | 연락처 없는 UA는 403 | `CONTACT_EMAIL` 필수, 워크플로우는 `MAIL_USERNAME` 사용 |
| 2026-09-15 | hnrss `points` 파라미터 | 502 | 파라미터 없이 사용 |
| 2026-09-15 | investor.nvidia.com RSS, HPCwire, VideoCardz | 403 | 제외 |
| 2026-09-17 | Autoware·TIER IV 소스 전체 | 개발 환경 egress 차단으로 실측 불가 (github.com만 도달) | 최초 도입. `crawl_only` 실행으로 실측하고 죽은 피드는 `enabled=False`로 내릴 것 |
| 2026-09-17 | autowarefoundation/autoware_universe 릴리스 Atom | 엔트리 2건 확인 (0.52.1, 0.52.0) | 사용 |
| 2026-09-17 | discourse.ros.org `/c/autoware/46` | 카테고리 존재 확인 (Discourse 규약상 `.rss`) | 사용 |
| 2026-09-17 | autoware.org | WordPress `/feed/` 관례 + `category/news/feed/` 확인 | `/feed/` 사용 |
| 2026-09-17 | TIER IV 자체 사이트 | RSS 없음 | Medium(`tier-iv-tech-blog`) + PR TIMES 기업 RDF + Google News 로 대체 |

## 장애 기록

- 2026-09-17 다주제 확장: `filters` 가 주제 키워드를 인자로 받게 바뀌면서 Autoware `business`
  정규식에 단어 경계 없는 `round`·`order`·`permit`·`invest` 를 넣었다가
  "robotics **round**up" 같은 제목이 통과. → 경계 추가 + `tests/test_filters.py` 신설.

- 2026-09-16 첫 Actions 실행(dry run): 카드 16건만으로 HTML 94KB → 크기 가드가 헤드라인을 3건만 남김.
  원인은 반복 inline 스타일(전체의 43%, 관련 기업 칩 57개 등). → 칩을 텍스트 한 줄로, 스타일 축약, 가드는 헤드라인 20건 보장 후 카드 강등.
  같은 실행에서 Google News 카드 3건이 원문 복원 실패로 헤드라인 강등 → 관련 보도 링크 폴백, 실패 시 요약 카드 유지, 실패 사유 로그.

- 2026-09-15 로컬 전량 실행: 채점 14배치 중 12배치 후 `You've hit your session limit`. 이후 모든 호출이 실패하며 건마다 재시도하고,
  크기 가드가 카드를 전부 강등해 카드 0·헤드라인 117건 메일이 생성됨.
  → 한도 오류 감지 시 이후 LLM 호출 즉시 중단 + 메일 안내 문구, 헤드라인 상한 40, 크기 가드는 헤드라인부터 축소, 카드 상한 25/15 → 15/10.

- 2026-08-20 ~ 09-15: 옛 `digest.yml`이 매일 `Verify Claude auth`에서 실패.
  로그: `Invalid Authorization header value from CLAUDE_CODE_OAUTH_TOKEN: it contains a line break at character 82`.
  시크릿 등록 시 줄바꿈 혼입. → `Auth preflight`에서 줄바꿈 제거 + 실제 호출 검증 + 실패 메일.
