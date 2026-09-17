# tech-monitoring

관심 기술 주제의 **사업·기술 동향**을 매일 자동 수집·분석해 한국어 HTML 리포트를 메일로 보냅니다.
주제마다 소스·키워드·채점 기준·메일 색이 따로 있고, 리포트도 주제별로 한 통씩 옵니다.

| 주제 | `--subject` | 메일 제목 | 중점 분야 (첫 섹션 고정 + 가중) |
|---|---|---|---|
| NVIDIA | `nvidia` | `[NVIDIA 모니터링]` | 자동차 · 로봇 (DRIVE · Isaac · Cosmos) |
| Autoware · TIER IV | `autoware` | `[Autoware 모니터링]` | 사업 · 서비스 배치 (투자 · 제휴 · 양산 · 실증) |

> 이전 이름: `nvidia-blog-digest` → `nvidia-monitoring` → `tech-monitoring`.
> 2026-09-15 NVIDIA 모니터링으로 전면 재설계, 2026-09-17 다주제로 확장. 옛 코드는 `legacy/`.

| 항목 | 내용 |
|---|---|
| 실행 | GitHub Actions, 매일 06:17 KST (`.github/workflows/monitor.yml`) — 주제별로 순차 실행 |
| 수집 대상 | 오늘 포함 최근 2일(KST) 발행분 중 아직 보내지 않은 항목 |
| LLM | Claude Code 헤드리스 (`claude -p`) — 1차 채점 haiku, 2차 심층 sonnet |
| 발송 | Gmail. 주제당 한 통. 신규 0건인 날도 발송하되 "소식 없음" 한 줄짜리 짧은 메일 |
| 결과물 | 메일, `archive/YYYY-MM-DD_{nv,aw}.json/.md`, 발송 이력 `state/seen_{nv,aw}.json` |

## 파이프라인

주제와 무관한 공통 흐름입니다. 대괄호 안 숫자는 주제별 설정(`subjects/*.py`)에서 옵니다.

```
[수집] 주제별 소스 — RSS/Atom, Google News(영/일/한), SEC 8-K, GitHub 릴리스, Hugging Face
   → 발송 이력(state/seen_*.json)에 있는 항목 제외
[Stage 0] 정규식 사전필터 — 공식·공시·릴리스는 통과, 매체는 주제 신호 필요, 딜·홍보성 제외
   → 제목 유사도 병합 (같은 소식 → 대표 1건 + "관련 보도")
[Stage 1] haiku 배치 채점 (10건씩, 동시 3배치) — 0~10점, 토픽, 중점 분야 여부, 한국어 제목·요약
   → 가중: 공식/공시 +1, 커뮤니티 -1, 중점 분야 +1
   → 한국어 제목 2차 병합
[분류] 카드(일반 5점+, 중점 4점+, 커뮤니티 7점+) / 헤드라인(2점+) / 릴리스·공시 보드
[Stage 2] sonnet 카드 심층 분석 (동시 4건) — 핵심 행동, 주요 사실, 왜 중요한가, 주제 관점, 중점 분야 관점
   → Google News 카드는 원문 URL 복원 → 관련 보도 링크 순으로 본문 확보, 모두 실패하면 요약 카드로 유지
[렌더] 핵심 3줄 → 목차 → 중점 분야(항상 첫 섹션) → 토픽별 섹션 → 릴리스·모델·공시 보드
```

상세 설계와 선정 기준은 [`docs/pipeline.md`](docs/pipeline.md).

## 주제 추가하기

`src/techmon/subjects/<key>.py` 파일 하나에 소스 목록·키워드·프롬프트 문구·토픽·색을 담고,
`subjects/__init__.py`에 한 줄 등록하면 끝입니다. 파이프라인 코드는 주제를 모릅니다.
자세한 필드 설명은 [`src/techmon/subjects/base.py`](src/techmon/subjects/base.py).

## 소스

### NVIDIA (`src/techmon/subjects/nvidia.py`)

| 분류 | 소스 |
|---|---|
| 공식 | Newsroom 보도자료, NVIDIA Blog (+Auto 카테고리), Technical Blog, YouTube 채널 |
| 공시 | SEC EDGAR 8-K (실적·중요 계약·임원 변동) |
| 릴리스 | GitHub 11개 저장소 (TensorRT, TensorRT-LLM, NeMo, Megatron-LM, cutlass, DALI, Isaac-GR00T, IsaacLab, Cosmos, Triton, VILA), Hugging Face nvidia 모델 |
| 해외 매체 | Tom's Hardware, The Next Platform, ServeTheHome, SemiAnalysis, TechCrunch·The Verge·Ars Technica(nvidia 태그), EE Times, DataCenterDynamics, CNBC Tech, Google News(NVIDIA / 자동차·로봇 검색) |
| 국내 매체 | 디일렉, 전자신문, IT조선, 한국경제 IT |
| 커뮤니티 | Hacker News, Reddit r/nvidia |

비활성: NVIDIA Research RSS(2021년 글만 남은 피드), Technical Blog AV·DRIVE 카테고리 피드(빈 피드).
차단으로 제외: investor.nvidia.com RSS, HPCwire, VideoCardz, ZDNet Korea.

### Autoware · TIER IV (`src/techmon/subjects/autoware.py`)

| 분류 | 소스 |
|---|---|
| 공식 | Autoware Foundation 블로그·뉴스, TIER IV MEDIA(Medium), TIER IV 보도자료(PR TIMES), YouTube Autoware Foundation 채널 |
| 릴리스 | autowarefoundation 9개 (autoware, autoware_core, autoware_universe, autoware_launch, autoware_msgs, AWSIM, vision_pilot, auto_e2e, agnocast), tier4 6개 (scenario_simulator_v2, nebula, CalibrationTools, AWML, caret, awkernel), Hugging Face tier4 모델 |
| 해외 매체 | The Robot Report, IEEE Spectrum Robotics, TechCrunch Transportation, Google News(Autoware / TIER IV / 사업 키워드) |
| TIER IV 회사 | Google News 기업 질의 2종 — 일본어(資金調達·上場·決算·買収·提携·人事·子会社), 영어(funding·IPO·revenue·acquisition·hires) |
| 일본 매체 | Google News 일본어판(ティアフォー·Autoware·レベル4), レスポンス |
| 국내 매체 | Google News 한국어판, 디일렉, 전자신문 |
| 커뮤니티 | ROS Discourse Autoware 카테고리, Hacker News, Reddit r/SelfDrivingCars |

**"Tier IV" 오탐 주의**: 데이터센터 등급(Uptime Institute)과 배출가스 규제(Tier 4 Final)에도
쓰이는 표현이라, 강한 신호가 그것뿐인데 해당 문맥까지 보이면 사전필터가 버립니다
(`Keywords.ambiguous` / `ambiguous_noise`). 회귀는 `tests/test_filters.py`가 지킵니다.

## 최초 설정

### 1. 저장소 시크릿

GitHub 저장소 → Settings → Secrets and variables → Actions.

| 이름 | 필수 | 설명 |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | ✅ (또는 아래) | `claude setup-token`으로 발급한 토큰 |
| `ANTHROPIC_API_KEY` | 선택 | 있으면 OAuth 토큰보다 우선 사용 (종량 과금, 만료 없음) |
| `MAIL_USERNAME` | ✅ | 발송 Gmail 주소. SEC 수집용 연락처로도 쓰임 |
| `MAIL_APP_PASSWORD` | ✅ | Gmail 앱 비밀번호 (https://myaccount.google.com/apppasswords) |
| `MAIL_TO` | 선택 | 수신자(콤마 구분). 없으면 `MAIL_USERNAME` |

**토큰 등록 시 주의**: 값에 줄바꿈이 섞이면 인증이 거부됩니다 (2026-08-20~09-15 장애 원인).
터미널에 붙여넣지 말고 아래처럼 등록하는 것이 안전합니다.

```bash
# 1) 별도 터미널에서 대화형으로 발급 — 출력된 토큰을 복사
claude setup-token

# 2) 줄바꿈 없이 등록 — 명령 실행 후 토큰을 붙여넣고 Enter, Ctrl+D
gh secret set CLAUDE_CODE_OAUTH_TOKEN -R JwonMoon/tech-monitoring
```

워크플로우의 `Auth preflight` 단계가 줄바꿈을 제거하고 실제 호출로 인증을 검증합니다. 실패하면 이후 단계를 실행하지 않고 실패 메일을 보냅니다.

### 2. 저장소 이름 바꾸기

저장소 안의 이름은 모두 `tech-monitoring`으로 맞춰져 있습니다. GitHub 쪽 이름은 직접 바꿔야 합니다.

1. GitHub 저장소 → Settings → General → Repository name → `tech-monitoring` → Rename
2. 로컬 remote 갱신: `git remote set-url origin git@github.com:JwonMoon/tech-monitoring.git`

GitHub가 옛 URL(`JwonMoon/nvidia-monitoring`)을 새 이름으로 리다이렉트하므로 기존 클론·링크도 당분간 동작합니다.

### 3. 수동 실행으로 확인

Actions 탭 → `Tech daily monitoring` → Run workflow.

| 입력 | 설명 |
|---|---|
| `subject` | `all`(기본) / `nvidia` / `autoware` |
| `target_date` | 기준 날짜 `YYYY-MM-DD`. 지정하면 발송 이력을 무시하고 그 날짜 기준으로 재수집 |
| `target_days` | 기준 날짜 포함 최근 N일 (기본 2) |
| `max_articles` | 채점 대상 제한 (테스트용, 0=무제한) |
| `crawl_only` | **LLM을 전혀 쓰지 않고** 소스별 수집 현황표만 생성. 소스 추가·점검용 |
| `dry_run` | 메일 발송·이력 저장·커밋 없이 결과물(artifact)만 생성 |
| `test_mail` | 실제 메일은 보내되 이력 저장·커밋은 하지 않음. 제목 앞에 `[테스트]` |

Gmail 설정만 빠르게 확인하려면 `Test email notification` 워크플로우를 실행합니다 (LLM 사용 없음, 1분 이내).

결과 HTML은 실행 페이지 하단 Artifacts에서 내려받아 확인할 수 있습니다.

## 로컬 실행 (Mac)

```bash
cd ~/moon_ws/tech-monitoring
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 키워드 회귀 테스트 (네트워크·LLM 불필요, 1초)
.venv/bin/python tests/test_filters.py

# LLM 없이 소스별 수집·사전필터 현황만 (1~2분)
.venv/bin/python src/run.py --crawl-only
.venv/bin/python src/run.py --subject autoware --crawl-only

# 소량 전체 실행 → out/<주제>/email.html 확인 (로컬은 발송 이력을 저장하지 않음)
MAX_ARTICLES=15 MAX_CARDS=4 .venv/bin/python src/run.py --subject autoware
open out/autoware/email.html

# 특정 날짜 기준
TARGET_DATE=2026-09-14 IGNORE_SEEN=1 .venv/bin/python src/run.py
```

주요 환경 변수 (`src/techmon/config.py`):

| 변수 | 기본값 | 설명 |
|---|---|---|
| `SUBJECT` | nvidia | 모니터링 주제. `--subject`가 우선 |
| `TARGET_DATE` / `TARGET_DAYS` | 오늘 / 2 | 수집 기간 (KST) |
| `STAGE1_MODEL` / `STAGE2_MODEL` | haiku / sonnet | 채점 / 심층 모델 |
| `STAGE1_WORKERS` / `STAGE2_WORKERS` | 3 / 4 | claude 동시 실행 수 |
| `MAX_ARTICLES` | 0 | 채점 대상 제한 |
| `MAX_CARDS` / `MAX_FOCUS_CARDS` | 주제별 (NVIDIA 15/10, Autoware 10/8) | 일반 / 중점 분야 카드 최대 |
| `MAX_HEADLINES` | 주제별 (NVIDIA 40, Autoware 30) | 일반 헤드라인 최대 (중점 분야 헤드라인은 전부 유지) |
| `MIN_HEADLINES` | 20 | 메일 크기 초과 시 카드 강등보다 먼저 보장하는 헤드라인 수 |
| `SOFT_DEADLINE_MIN` | 45 | 초과 시 남은 카드는 헤드라인으로 강등 |
| `WRITE_STATE` | 0 (CI는 1) | 발송 이력 저장 여부 |
| `IGNORE_SEEN` | 0 | 발송 이력 무시 |
| `CONTACT_EMAIL` | 없음 | SEC 수집용 연락처. 없으면 SEC만 건너뜀 |
| `MAIL_MODE` | file | `smtp`면 Gmail로 직접 발송 (`MAIL_USERNAME`, `MAIL_APP_PASSWORD` 필요) |
| `LLM_BACKEND` | claude | `exacode`면 사내 tach CLI |
| `OUT_DIR` | `out/<주제>` | 결과물 경로 |

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| `Auth preflight` 실패 | 토큰 재발급 후 위 방법으로 줄바꿈 없이 재등록 |
| 메일이 안 옴 | `MAIL_APP_PASSWORD`가 앱 비밀번호인지, 스팸함 |
| 한 주제만 메일이 옴 | 다른 주제 잡이 실패한 것. Actions에서 `monitor (주제)` 잡 로그 확인 (`fail-fast: false`라 한쪽 실패가 나머지를 막지 않음) |
| 특정 소스 0건·오류 | `crawl_only` 실행 결과의 오류 칸 / 메일 하단 "수집 실패" 목록 |
| 엉뚱한 기사가 섞임 | `tests/test_filters.py`에 사례를 추가하고 `subjects/<주제>.py`의 키워드를 조이기 |
| 같은 소식이 반복됨 | `state/seen_*.json`이 커밋되는지 (Commit archive and state 단계) |
| 실행이 60분 초과 | `STAGE2_WORKERS` 증가 또는 `MAX_CARDS` 감소 |
| 메일에 "LLM 사용 한도 초과" 안내 | Claude 구독 한도 소진. 두 주제가 한도를 나눠 쓰므로 `MAX_CARDS` 감소 또는 `ANTHROPIC_API_KEY` 사용 |

## 구조

```
tech-monitoring/
├── .github/workflows/monitor.yml   # 데일리 실행 (주제별 매트릭스)
├── src/
│   ├── run.py                      # 엔트리포인트 (--subject / --crawl-only)
│   └── techmon/
│       ├── config.py               # 환경 변수·임계값 (주제를 import 시점에 확정)
│       ├── subjects/
│       │   ├── base.py             # Subject / Keywords / Prompt 정의
│       │   ├── __init__.py         # 주제 레지스트리
│       │   ├── nvidia.py           # NVIDIA 소스·키워드·프롬프트
│       │   └── autoware.py         # Autoware · TIER IV 소스·키워드·프롬프트
│       ├── sources.py              # Source 레코드, gnews()·github_releases() 빌더
│       ├── crawl.py                # 수집·정규화·원문 추출
│       ├── filters.py              # Stage 0 사전필터 (주제 키워드를 받는 순수 함수)
│       ├── prompts.py              # LLM 프롬프트 틀
│       ├── llm.py                  # claude / exacode 호출
│       ├── pipeline.py             # 채점·병합·분류·심층·핵심 3줄
│       ├── render.py               # HTML 메일
│       ├── archive.py              # 일별 보관
│       ├── state.py                # 발송 이력
│       └── mailer.py               # 로컬 SMTP 발송
├── tests/test_filters.py           # Stage 0 키워드 회귀 (네트워크·LLM 불필요)
├── archive/                        # 일별 결과 (자동 커밋)
├── state/seen_{nv,aw}.json         # 주제별 발송 이력 (자동 커밋, 30일 보존)
├── docs/pipeline.md                # 설계 문서
└── legacy/                         # 옛 nvidia-blog-digest 코드·결과물
```
