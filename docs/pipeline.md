# NVIDIA 모니터링 파이프라인 설계

> 2026-09-15 기준. 사내 `ad-newsletter`의 데일리 뉴스 파이프라인(`ad_news_exa.py`) 구조를 NVIDIA 전 분야로 확장.

## 목표와 원칙

- NVIDIA 사업(실적·규제·공급망·파트너십)과 기술(GPU·데이터센터·SDK·모델·연구)을 빠짐없이 모니터링
- 자동차·로봇은 가중 + 첫 섹션 고정 + 헤드라인 이하로 탈락하지 않음
- 공식 1차 출처(Newsroom·SEC·GitHub·HF)를 매체 보도보다 우선
- 같은 소식은 한 번만, 여러 매체 보도는 "관련 보도"로 묶음
- 매일 발송, 0건인 날도 알림 (파이프라인 생존 확인)

## 수집 기간과 중복 방지

- 기간: 기준일(KST) 포함 최근 `TARGET_DAYS`(기본 2)일
- 06:17 KST 실행 시 "어제만" 보면 전날 06:17 이후 발행분 중 일부를 영구 누락할 수 있어 2일 창을 쓴다
- 겹치는 하루는 `state/seen.json`으로 제거. 채점된 항목의 uid(병합된 관련 보도 포함)를 기록하고 30일 뒤 삭제
- uid: 추적 파라미터를 뺀 정규화 URL, GitHub는 `gh:저장소:태그`, HF는 `hf:모델:new|날짜`, SEC는 `sec:접수번호`
- 로컬 실행은 기본적으로 이력을 쓰지 않는다 (`WRITE_STATE=0`)

## 소스 kind별 정규화 (`crawl.py`)

| kind | 처리 |
|---|---|
| feed | RSS `item` / Atom `entry` 공통 파싱. 본문 300자 미만이면 trafilatura로 원문 보강 (`fetch_full=True` 소스만) |
| gnews | 제목 끝 ` - 매체명` 분리, 출처를 `Google News · 매체명`으로 표기. 본문 없음 → 카드 승격 시에만 `googlenewsdecoder`로 원문 URL 복원 후 추출 |
| sec | 8-K Atom의 `filing-date`, `items-desc`, `accession-number` 사용. Item 코드를 한국어 설명으로 변환 (2.02=실적, 1.01=중요 계약, 5.02=임원 등). User-Agent에 연락처 필수 |
| github | 릴리스 Atom. 태그와 릴리스 노트 2,000자 |
| hf | 모델 목록 API. `createdAt`이 기간 내면 신규, `lastModified`만 바뀐 건 워치리스트(Cosmos·Alpamayo·GR00T·Isaac·Nemotron 등)만 업데이트로 포함. 하루 최대 15건, README 1,500자 |

## Stage 0 사전필터 (`filters.py`)

- 공식·공시·릴리스 소스(`prefilter=False`)는 무조건 통과
- 매체·커뮤니티: `STRONG_KW`(NVIDIA·제품·플랫폼·임원명) 필수
  - 제목에 없고 본문에 1회뿐이면 `BUSINESS_KW`(실적·규제·공급망) 또는 `AUTO_KW`(자동차·로봇) 동반 필요
- 제목에 딜·할인·게이밍 벤치마크·설치 가이드 표현이 있으면 제외 (자동차·로봇 신호가 있으면 예외)
- 주가 기사는 제외하지 않음 → 채점 3~4점 헤드라인

## Stage 1 채점 기준 (`prompts.STAGE1`)

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

- 최종 점수 = LLM 점수 + 소스 가중(공식·공시 +1, SemiAnalysis·Next Platform +1, 커뮤니티 -1) + 자동차·로봇 +1
- 자동차·로봇 판정 = LLM `is_auto` OR `AUTO_KW` 정규식 OR 자동차 전용 피드
- 자동차·로봇 항목은 최소 헤드라인 점수 보장
- 카드 기준: 일반 5, 자동차·로봇 4, 커뮤니티 7, 릴리스·공시 7 (미만은 보드)
- 카드 상한: 일반 15, 자동차·로봇 10. 넘치면 헤드라인으로
- 헤드라인 상한: 일반 40건 (자동차·로봇 헤드라인은 전부 유지). 넘친 저점 항목은 archive에만 기록
- 메일 HTML이 95KB를 넘으면: 일반 헤드라인을 20건까지 저점부터 제거 → 저점 카드를 헤드라인으로 강등 → 남은 일반 헤드라인 제거 (Gmail 102KB 클리핑). 자동차·로봇 헤드라인은 제거하지 않음

## 병합 (`merge_duplicates`)

1. Stage 1 전: uid 동일 또는 제목 유사도(SequenceMatcher) 0.85 이상
2. Stage 1 후: 한국어 제목 유사도 0.8 이상 + 같은 토픽 (영문·한글 보도 중복)
- 대표 우선순위: 공식 > 공시 > 릴리스 > 해외 매체 > 국내 매체 > Google News > 커뮤니티
- 릴리스 항목과 15자 미만 제목은 유사도 병합 대상에서 제외

## Stage 2 심층 분석 (`prompts.STAGE2`)

카드마다 JSON: `action{actor, action, stage, timeline, scope}`, `key_facts`, `why_matters`, `nvidia_angle`, `auto_robotics_angle`(자동차·로봇만), `companies`, `products`, `watch_next`.
본문에 없는 내용은 "미확인" — 렌더 시 숨김.

본문 확보: Google News 카드는 `googlenewsdecoder`로 원문 URL 복원 → 실패하면 병합된 관련 보도 중 Google News가 아닌 링크에서 추출.
모두 실패하면 LLM 분석 없이 1차 요약만 담은 카드로 유지하고 "원문 본문을 가져오지 못해" 문구를 표시한다 (중요 소식 누락 방지).

## 실행 시간 예산

2026-09-15 측정: 전 소스 수집 약 1.5분, 원시 307건 → 사전필터 158건 → 병합 133건.
심층 분석은 sonnet 기준 건당 약 1분이라 `STAGE2_WORKERS=4`로 병렬 처리.
`SOFT_DEADLINE_MIN=45`를 넘기면 남은 카드는 분석 없이 헤드라인으로 내려 60분 잡 제한 안에서 끝낸다.

## 소스 점검 기록

| 날짜 | 소스 | 상태 | 조치 |
|---|---|---|---|
| 2026-09-15 | NVIDIA Research RSS | 2021년 글만 남음 | 비활성 |
| 2026-09-15 | Technical Blog AV·DRIVE 카테고리 피드 | 엔트리 0건 | 비활성 (전체 Technical Blog + 자동차 키워드로 커버) |
| 2026-09-15 | 한국경제 IT | 전체 Chrome UA는 403 | 짧은 UA(`simple`) 사용 |
| 2026-09-15 | SEC EDGAR | 연락처 없는 UA는 403 | `CONTACT_EMAIL` 필수, 워크플로우는 `MAIL_USERNAME` 사용 |
| 2026-09-15 | hnrss `points` 파라미터 | 502 | 파라미터 없이 사용 |
| 2026-09-15 | investor.nvidia.com RSS, HPCwire, VideoCardz | 403 | 제외 |

## 장애 기록

- 2026-09-16 첫 Actions 실행(dry run): 카드 16건만으로 HTML 94KB → 크기 가드가 헤드라인을 3건만 남김.
  원인은 반복 inline 스타일(전체의 43%, 관련 기업 칩 57개 등). → 칩을 텍스트 한 줄로, 스타일 축약, 가드는 헤드라인 20건 보장 후 카드 강등.
  같은 실행에서 Google News 카드 3건이 원문 복원 실패로 헤드라인 강등 → 관련 보도 링크 폴백, 실패 시 요약 카드 유지, 실패 사유 로그.

- 2026-09-15 로컬 전량 실행: 채점 14배치 중 12배치 후 `You've hit your session limit`. 이후 모든 호출이 실패하며 건마다 재시도하고,
  크기 가드가 카드를 전부 강등해 카드 0·헤드라인 117건 메일이 생성됨.
  → 한도 오류 감지 시 이후 LLM 호출 즉시 중단 + 메일 안내 문구, 헤드라인 상한 40, 크기 가드는 헤드라인부터 축소, 카드 상한 25/15 → 15/10.

- 2026-08-20 ~ 09-15: 옛 `digest.yml`이 매일 `Verify Claude auth`에서 실패.
  로그: `Invalid Authorization header value from CLAUDE_CODE_OAUTH_TOKEN: it contains a line break at character 82`.
  시크릿 등록 시 줄바꿈 혼입. → `Auth preflight`에서 줄바꿈 제거 + 실제 호출 검증 + 실패 메일.
