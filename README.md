# nvidia-monitoring

NVIDIA의 사업·기술 동향을 매일 자동 수집·분석해 한국어 HTML 리포트를 메일로 보냅니다.
자동차·로봇(DRIVE, Thor, Alpamayo, Cosmos, Isaac, GR00T)은 가중치를 주고 첫 섹션에 고정합니다.

> 이전 이름: `nvidia-blog-digest` (개발자 블로그 1개 요약). 2026-09-15 전면 재설계. 옛 코드와 결과물은 `legacy/`에 보관.

| 항목 | 내용 |
|---|---|
| 실행 | GitHub Actions, 매일 06:17 KST (`.github/workflows/monitor.yml`) |
| 수집 대상 | 오늘 포함 최근 2일(KST) 발행분 중 아직 보내지 않은 항목 |
| LLM | Claude Code 헤드리스 (`claude -p`) — 1차 채점 haiku, 2차 심층 sonnet |
| 발송 | Gmail. 신규 0건인 날도 "신규 0건" 알림 메일 발송 |
| 결과물 | 메일, `archive/YYYY-MM-DD_nv.json/.md`, 발송 이력 `state/seen.json` |

## 파이프라인

```
[수집] 소스 39개(활성 36개) — RSS/Atom, Google News, SEC 8-K, GitHub 릴리스, Hugging Face
   → 발송 이력(state/seen.json)에 있는 항목 제외
[Stage 0] 정규식 사전필터 — 공식·공시·릴리스는 통과, 매체는 NVIDIA 신호 필요, 딜·게이밍 리뷰 제외
   → 제목 유사도 병합 (같은 소식 → 대표 1건 + "관련 보도")
[Stage 1] haiku 배치 채점 (10건씩, 동시 3배치) — 0~10점, 토픽, 자동차·로봇 여부, 한국어 제목·요약
   → 가중: 공식/공시 +1, 커뮤니티 -1, 자동차·로봇 +1
   → 한국어 제목 2차 병합
[분류] 카드(일반 5점+, 자동차·로봇 4점+, 커뮤니티 7점+) / 헤드라인(2점+) / 릴리스·공시 보드
[Stage 2] sonnet 카드 심층 분석 (동시 4건) — 핵심 행동, 주요 사실, 왜 중요한가, NVIDIA 관점, 자동차·로봇 관점
   → Google News 카드는 원문 URL 복원 → 관련 보도 링크 순으로 본문 확보, 모두 실패하면 요약 카드로 유지
[렌더] 핵심 3줄 → 목차 → 자동차·로봇(항상 첫 섹션) → 토픽별 섹션 → 릴리스·모델·공시 보드
```

상세 설계와 선정 기준은 [`docs/pipeline.md`](docs/pipeline.md).

## 소스

소스 목록은 [`src/nvmon/sources.py`](src/nvmon/sources.py) 한 곳에서 관리합니다. 추가는 한 줄.

| 분류 | 소스 |
|---|---|
| NVIDIA 공식 | Newsroom 보도자료, NVIDIA Blog (+Auto 카테고리), Technical Blog, YouTube 채널 |
| 공시 | SEC EDGAR 8-K (실적·중요 계약·임원 변동) |
| 릴리스 | GitHub 11개 저장소 (TensorRT, TensorRT-LLM, NeMo, Megatron-LM, cutlass, DALI, Isaac-GR00T, IsaacLab, Cosmos, Triton, VILA), Hugging Face nvidia 모델 |
| 해외 매체 | Tom's Hardware, The Next Platform, ServeTheHome, SemiAnalysis, TechCrunch·The Verge·Ars Technica(nvidia 태그), EE Times, DataCenterDynamics, CNBC Tech, Google News(NVIDIA / 자동차·로봇 검색) |
| 국내 매체 | 디일렉, 전자신문, IT조선, 한국경제 IT |
| 커뮤니티 | Hacker News, Reddit r/nvidia |

비활성: NVIDIA Research RSS(2021년 글만 남은 피드), Technical Blog AV·DRIVE 카테고리 피드(빈 피드). 차단으로 제외: investor.nvidia.com RSS, HPCwire, VideoCardz, ZDNet Korea.

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
gh secret set CLAUDE_CODE_OAUTH_TOKEN -R JwonMoon/nvidia-monitoring
```

워크플로우의 `Auth preflight` 단계가 줄바꿈을 제거하고 실제 호출로 인증을 검증합니다. 실패하면 이후 단계를 실행하지 않고 실패 메일을 보냅니다.

### 2. 수동 실행으로 확인

Actions 탭 → `NVIDIA daily monitoring` → Run workflow.

| 입력 | 설명 |
|---|---|
| `target_date` | 기준 날짜 `YYYY-MM-DD`. 지정하면 발송 이력을 무시하고 그 날짜 기준으로 재수집 |
| `target_days` | 기준 날짜 포함 최근 N일 (기본 2) |
| `max_articles` | 채점 대상 제한 (테스트용, 0=무제한) |
| `dry_run` | 체크하면 메일 발송·이력 저장·커밋 없이 결과물(artifact)만 생성 |
| `test_mail` | 체크하면 실제 메일을 보내되 이력 저장·커밋은 하지 않음. 제목 앞에 `[테스트]` |

Gmail 설정만 빠르게 확인하려면 `Test email notification` 워크플로우를 실행합니다 (LLM 사용 없음, 1분 이내).

결과 HTML은 실행 페이지 하단 Artifacts에서 내려받아 확인할 수 있습니다.

## 로컬 실행 (Mac)

```bash
cd ~/moon_ws/nvidia-monitoring
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# LLM 없이 소스별 수집·사전필터 현황만 (1~2분)
.venv/bin/python src/run.py --crawl-only

# 소량 전체 실행 → out/email.html 확인 (로컬은 발송 이력을 저장하지 않음)
MAX_ARTICLES=15 MAX_CARDS=4 .venv/bin/python src/run.py
open out/email.html

# 특정 날짜 기준
TARGET_DATE=2026-09-14 IGNORE_SEEN=1 .venv/bin/python src/run.py
```

주요 환경 변수 (`src/nvmon/config.py`):

| 변수 | 기본값 | 설명 |
|---|---|---|
| `TARGET_DATE` / `TARGET_DAYS` | 오늘 / 2 | 수집 기간 (KST) |
| `STAGE1_MODEL` / `STAGE2_MODEL` | haiku / sonnet | 채점 / 심층 모델 |
| `STAGE1_WORKERS` / `STAGE2_WORKERS` | 3 / 4 | claude 동시 실행 수 |
| `MAX_ARTICLES` | 0 | 채점 대상 제한 |
| `MAX_CARDS` / `MAX_AUTO_CARDS` | 15 / 10 | 일반 / 자동차·로봇 카드 최대 |
| `MAX_HEADLINES` | 40 | 일반 헤드라인 최대 (자동차·로봇 헤드라인은 전부 유지) |
| `MIN_HEADLINES` | 20 | 메일 크기 초과 시 카드 강등보다 먼저 보장하는 헤드라인 수 |
| `SOFT_DEADLINE_MIN` | 45 | 초과 시 남은 카드는 헤드라인으로 강등 |
| `WRITE_STATE` | 0 (CI는 1) | 발송 이력 저장 여부 |
| `IGNORE_SEEN` | 0 | 발송 이력 무시 |
| `CONTACT_EMAIL` | 없음 | SEC 수집용 연락처. 없으면 SEC만 건너뜀 |
| `MAIL_MODE` | file | `smtp`면 Gmail로 직접 발송 (`MAIL_USERNAME`, `MAIL_APP_PASSWORD` 필요) |
| `LLM_BACKEND` | claude | `exacode`면 사내 tach CLI |

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| `Auth preflight` 실패 | 토큰 재발급 후 위 방법으로 줄바꿈 없이 재등록 |
| 메일이 안 옴 | `MAIL_APP_PASSWORD`가 앱 비밀번호인지, 스팸함 |
| 특정 소스 0건·오류 | 메일 하단 "수집 실패" 목록 / `--crawl-only` 결과의 오류 칸 |
| 같은 소식이 반복됨 | `state/seen.json`이 커밋되는지 (Commit archive and state 단계) |
| 실행이 60분 초과 | `STAGE2_WORKERS` 증가 또는 `MAX_CARDS` 감소 |
| 메일에 "LLM 사용 한도 초과" 안내 | Claude 구독 한도 소진. 이후 호출은 자동 중단되고 기본 점수로 발송됨. 반복되면 `MAX_CARDS` 감소 또는 `ANTHROPIC_API_KEY` 사용 |

## 구조

```
nvidia-monitoring/
├── .github/workflows/monitor.yml   # 데일리 실행
├── src/
│   ├── run.py                      # 엔트리포인트
│   └── nvmon/
│       ├── config.py               # 환경 변수·임계값
│       ├── sources.py              # 소스 레지스트리
│       ├── crawl.py                # 수집·정규화·원문 추출
│       ├── filters.py              # Stage 0 키워드
│       ├── prompts.py              # LLM 프롬프트
│       ├── llm.py                  # claude / exacode 호출
│       ├── pipeline.py             # 채점·병합·분류·심층·핵심 3줄
│       ├── render.py               # HTML 메일
│       ├── archive.py              # 일별 보관
│       ├── state.py                # 발송 이력
│       └── mailer.py               # 로컬 SMTP 발송
├── archive/                        # 일별 결과 (자동 커밋)
├── state/seen.json                 # 발송 이력 (자동 커밋, 30일 보존)
├── docs/pipeline.md                # 설계 문서
└── legacy/                         # 옛 nvidia-blog-digest 코드·결과물
```
