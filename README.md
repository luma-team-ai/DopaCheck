# 🧠 도파민 체크 (Dopamine Check)

> ⚠️ **[개발팀 공지] 2026-06-12 — DB가 MariaDB로 전환됨(#22).** 작업 전 **[리베이스 가이드](docs/REBASE_GUIDE_mariadb.md)** 필독, 각자 브랜치 `git rebase origin/main` 필요. *(전원 리베이스 완료 후 이 배너 제거)*

> 배달 한 번, 스크롤 한 시간 — 내 도파민 소비를 숫자로 마주하는 서비스

배달 영수증을 올리면 **"치킨 1.2마리값, 러닝 28분어치"** 로, SNS·게임 시간을 입력하면 **"책 2권, 시급 N원짜리 취미"** 로 환산해 보여줍니다. AI가 공감 코멘트와 맞춤 챌린지를 제안하고, 종합 도파민 점수로 소비 패턴 변화를 추적합니다.

> ℹ️ 이 README의 위쪽(서비스 소개)은 배포·발표 시점에 실사용자용으로 계속 키워나가고, 아래쪽 **개발팀 가이드**는 추후 `docs/`로 이동할 예정입니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| 🍗 배달 분석 | 영수증 사진 업로드 → OCR 자동 추출 → 지출·칼로리 환산 + AI 코멘트 |
| ⏰ 시간 분석 | 앱별 사용 시간 입력 → 대체 활동 환산 + 도넛 차트 |
| 📊 종합 리포트 | 통합 대시보드 + 주간 비교 + SNS 공유 카드 |
| 🔥 도파민 점수 | 0~100 점수 산출, 전체 평균 대비 / 상위 N% 랭킹 |
| 🏆 AI 챌린지 | 내 히스토리 기반 맞춤 챌린지 추천, 달성 시 보너스 점수 |

**기술 스택**: Flask · Jinja2 · MariaDB · OAuth(Google·Kakao) · Claude API · Cloudtype

> 🔄 **DB 변경 이력**: Supabase(PostgreSQL + Auth + RLS) → **MariaDB**(앱 레벨 `user_id` 필터, 소셜로그인 직접 연동)로 전환됨 (#22).

---

# 🛠 개발팀 가이드

> AI 심화 과정 6인 팀 프로젝트 · 개발 기간 6~7일 · 상세 스펙은 [PRD](docs/PRD.md) 참조

## 🔄 DB 전환 이력 (#22) — 트러블슈팅 참조

PR #22(`51be2ed`)로 main이 **Supabase → MariaDB**로 전환됨 (PRD Ver1.1 §11 ERD 정합). 전환 전후로 작성된 코드/PR이 섞여 있어, 아래 항목에서 에러가 나면 "이전 → 현재" 기준으로 확인하세요. (리베이스 절차: [REBASE_GUIDE](docs/REBASE_GUIDE_mariadb.md))

| 영역 | 이전 (Supabase) | 현재 (MariaDB, #22~) |
|------|-----------------|----------------------|
| DB 접근 | `from db.client import get_supabase` · `get_supabase().table(...).select()...` | `from db.client import db` · `with db() as cursor: cursor.execute("... %s", (...))` |
| 의존성 | `supabase` | `pymysql` |
| env | `SUPABASE_URL` / `SUPABASE_KEY` / `SUPABASE_SERVICE_KEY` | `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` |
| 사용자 격리 | RLS(행 수준 보안) | 앱 레벨 — 모든 쿼리에 `WHERE user_id = %s` (#21) |
| 사용자 식별 | `auth.users`(Supabase Auth) | `users.(provider, provider_id)` upsert (#26) — `provider/provider_id` 컬럼 필수 |
| 주차 경계 | `kst_bounds` → `+09:00` ISO 문자열 | `kst_bounds` → `"YYYY-MM-DD HH:MM:SS"`, DB 세션 TZ `+09:00` 고정 (#11) |
| 세션 | `session["user"]["id"]` | `session.get("user_id")` (falsy면 `abort(401)`) |

**자주 깨지는 지점**: ① `get_supabase` import 잔재 → `ImportError` ② 쿼리에 `WHERE user_id` 누락 → 타 사용자 데이터 노출 ③ `provider/provider_id` 미반영 브랜치 → `SELECT ... provider` SQL 에러 (#26 해결).

## 1. 빠른 시작

```bash
git clone https://github.com/luma-team-ai/dopacheck.git
cd dopacheck

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 값은 팀 채널에서 공유 (절대 커밋 금지!)

flask --app app run --debug   # http://localhost:5000
pytest                        # 테스트
```

## 2. 프로젝트 구조

```
dopacheck/
├── app.py            Flask 진입점 — Blueprint 등록 (공통 수정은 팀 합의 후)
├── config.py         환산 기준 상수 (⚠️ 초안 — 팀 합의로 확정)
├── ai/               AI 모듈 (오영석) — 라우트에서 직접 함수 호출
│   ├── ocr.py        영수증 파싱        ai.ocr.parse_receipt(image_bytes)
│   ├── calorie.py    칼로리 추론        ai.calorie.estimate(items)
│   ├── comment.py    공감 코멘트        ai.comment.generate(type, context)
│   ├── score.py      점수 산출          ai.score.calculate(data)
│   └── challenge.py  챌린지 추천        ai.challenge.recommend(history)
├── routes/           도메인별 Blueprint (담당자별 — 아래 표)
├── db/
│   ├── client.py     get_connection()/db() 단일 팩토리 (pymysql — 직접 connect 금지)
│   └── schema.sql    DB 스키마 (MariaDB — RLS 제거, 앱 레벨 user_id 필터)
├── templates/        Jinja2 — base.html 상속, 도메인별 폴더
├── static/           CSS/JS
├── tests/            pytest — 도메인별 test_*.py (스텁에 skip 마커)
└── docs/STATUS.md    진행 현황판
```

## 3. 역할 분담

| 담당 | 영역 | 작업 파일 | 요구사항 |
|------|------|----------|----------|
| **김승현** | 인증 + 점수 + DB | `routes/auth.py` `routes/score.py` `db/` | FR-0, FR-26~31 + MariaDB·OAuth·시드 데이터 |
| **김관영** | 배달 분석 | `routes/delivery.py` `templates/delivery/` | FR-1~8 + Cloudtype 서버 |
| **이은석** | 시간 분석 | `routes/time.py` `templates/time/` | FR-9~15 + Cloudtype 배포 |
| **정재봉** | 종합 리포트 | `routes/report.py` `templates/report/` | FR-16~20 + 레포 관리·브랜치 전략 |
| **허남** | 히스토리 | `routes/history.py` `templates/history/` | FR-21~25 |
| **오영석** | AI 모듈 + 챌린지 | `ai/` `routes/challenge.py` `templates/challenge/` | FR-32~45 |

### 담당자별 시작 가이드

모든 스텁에 `TODO(이름)` 주석과 FR 번호가 달려 있습니다. **자기 파일 안의 TODO만 채우면 됩니다.**

- **공통**: 페이지 라우트에 `@login_required` 유지 · AI 호출은 `try/except`로 감싸고 실패 시 수동 입력 fallback (FR-45) · DB는 `db.client.get_connection()`/`db()`만 사용 · 분석 저장 후 `routes.score.recalculate_score(user_id)` 호출 (FR-31)
- **김승현**: 최우선(다른 팀원 블로커) — ① `db/schema.sql` MariaDB 적용 ② OAuth 연동 ③ `recalculate_score()` 구현
- **오영석**: `ai/` 함수 시그니처·반환 dict 형식은 docstring에 고정되어 있음 — **형식 변경 시 팀 공지 필수** (다른 사람 코드가 의존)
- **김관영·이은석·정재봉·허남**: 김승현·오영석 작업 완료 전에는 더미 dict로 화면 먼저 개발 가능

## 4. 협업 규칙

### 브랜치 전략
- `main` = 항상 동작하는 상태 유지. **main 직접 push 금지**
- 브랜치명: `feat/{영역}-{내용}` (예: `feat/delivery-ocr`, `feat/score-ranking`)
- 작업 흐름: 브랜치 생성 → 구현 → `pytest` PASS 확인 → PR → **다른 팀원 1인 리뷰** → 머지

### 커밋 컨벤션
```
feat: 영수증 OCR 파싱 연동
fix: 시간 환산 0 입력 시 오류 수정
docs: README 역할 분담 갱신
chore: 의존성 추가
```

### 충돌 방지
- **자기 담당 파일만 수정** — `app.py`·`base.html`·`config.py`·`schema.sql` 등 공통 파일 수정은 팀 채널 합의 후
- `ai/` 함수 인터페이스(입출력 dict)와 DB 스키마 변경은 **변경 전 공지** 필수
- 머지 순서: 인증/DB(김승현) → AI 모듈(오영석) → 각 도메인

### 보안 (전원 필수)
- `.env` 절대 커밋 금지 — 키는 팀 채널로만 공유, 코드에 하드코딩 금지
- 커밋 전 diff에 API 키·시크릿 포함 여부 확인
- 사용자 데이터 조회는 항상 본인(user_id) 스코프 — 모든 쿼리에 `WHERE user_id=%s` 앱 레벨 필터 (RLS 제거됨, #21)

## 5. 일정 가이드 (6~7일)

| Day | 목표 |
|-----|------|
| 1 | 환경 세팅 · MariaDB 스키마 적용 · OAuth 연동 · 점수 공식/상수 합의 |
| 2~4 | 도메인별 병렬 구현 (화면 → 로직 → AI 연동 → 저장) |
| 5 | 통합 테스트: 업로드→OCR→저장→히스토리→점수 전체 흐름 (PRD §9) |
| 6 | 데모 시나리오 완주 · 모바일(Chrome/Safari) QA · 시드 데이터·랭킹 확인 |
| 7 | 버퍼 · 발표 준비 |

## 6. 환경변수

| 변수 | 설명 | 관리 |
|------|------|------|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MariaDB 연결 | 김승현 |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `KAKAO_CLIENT_ID` | OAuth | 김승현 |
| `ANTHROPIC_API_KEY` | Claude API | 오영석 |
| `FLASK_SECRET_KEY` | 세션 암호화 | 김관영 |

## 팀

김승현 · 김관영 · 이은석 · 정재봉 · 허남 · 오영석
