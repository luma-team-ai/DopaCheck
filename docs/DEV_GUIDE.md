# 🛠 개발팀 가이드 — Dopamine Check

> AI 심화 과정 6인 팀 프로젝트 · 개발 기간 6~7일
>
> 📋 **[진행 현황 & 할 일 보드 → STATUS.md](STATUS.md)** · 📑 상세 스펙 **[PRD](PRD.md)** · 🔁 리베이스 절차 **[REBASE_GUIDE](REBASE_GUIDE_mariadb.md)**

이 문서는 **기여자(개발팀)용**입니다. 서비스 소개·빠른 시작은 루트 [README](../README.md)를 참조하세요.

---

## 1. 로컬 개발 환경

> **Python 3.10+ 필수** (배포 타깃 `3.10.2` — `runtime.txt`·`.python-version` 고정). 소셜로그인 의존성 `authlib>=1.7`이 Python 3.10+를 요구하므로 3.9에서는 설치·실행 불가.

```bash
git clone https://github.com/luma-team-ai/dopacheck.git
cd dopacheck

python3.10 -m venv .venv && source .venv/bin/activate   # 3.10+ 인터프리터
pip install -r requirements.txt

cp .env.example .env   # 값은 팀 채널에서 공유 (절대 커밋 금지!)

flask --app app run --debug   # http://localhost:5000
pytest                        # 테스트
```

### CSS 빌드 (Tailwind, #49)

`base.html`·`login.html`은 Play CDN 대신 **빌드된 `static/css/tailwind.css`(커밋됨)** 를 사용한다. 배포(CloudType `python` 빌드팩)는 이 산출물을 그대로 서빙하므로 **Node 빌드가 배포에 필요 없다**. 단, `templates/*.html`에서 Tailwind 클래스를 추가/변경하면 **반드시 재빌드 후 산출물을 커밋**해야 한다(안 하면 새 클래스가 누락돼 시각 회귀가 무음으로 발생).

```bash
npm install                # 최초 1회 (package-lock.json 기준 재현)
npm run build:css          # templates 스캔 → static/css/tailwind.css 재빌드 (minify)
npm run watch:css          # 개발 중 자동 재빌드 (커밋 전엔 build:css로 minify 확정)
```

---

## 2. 프로젝트 구조

```
dopacheck/
├── app.py            Flask 진입점 — Blueprint 등록 (공통 수정은 팀 합의 후)
├── config.py         환산 기준 상수·모델 상수
├── ai/               AI 모듈 (오영석) — 라우트에서 직접 함수 호출
│   ├── ocr.py        영수증 파싱        ai.ocr.parse_receipt(image_bytes)
│   ├── image_prep.py OCR 전처리(리사이즈·EXIF·대비, #199)
│   ├── calorie.py    칼로리 추론        ai.calorie.estimate(items)
│   ├── comment.py    공감 코멘트        ai.comment.generate(type, context)
│   ├── score.py      점수 산출          ai.score.calculate(data)
│   ├── challenge.py  챌린지 추천        ai.challenge.recommend(history)
│   └── utils.py      공통 — get_client()(타임아웃 팩토리)·extract_json()·extract_text()
├── routes/           도메인별 Blueprint (담당자별 — 아래 표)
├── services/         도메인 서비스 (score_service.recalculate_score 등)
├── scheduler/        주간 챌린지 정산 배치 (멀티워커 advisory lock, #206)
├── db/
│   ├── client.py     get_connection()/db() 단일 팩토리 (pymysql 풀 — 직접 connect 금지)
│   ├── schema.sql    DB 스키마 (MariaDB — RLS 제거, 앱 레벨 user_id 필터)
│   ├── seed.sql      시드 데이터
│   └── migrations/   운영 ALTER 마이그레이션 (001~004, 수동 적용)
├── templates/        Jinja2 — base.html / _app_base.html 상속, 도메인별 폴더
├── static/           CSS/JS (tailwind.css 산출물 커밋)
├── tests/            pytest — 도메인별 test_*.py
└── docs/             STATUS.md(현황) · PRD.md(스펙) · DEV_GUIDE.md(이 문서)
```

---

## 3. 역할 분담 (영구 도메인 담당)

> 🎯 지금 당장 할 일·우선순위는 **[STATUS.md 스프린트 보드](STATUS.md#sprint)** 참조. 아래 표는 변하지 않는 책임 영역.

| 담당 | 영역 | 작업 파일 | 요구사항 |
|------|------|----------|----------|
| **김승현** | 인증 + 점수 + DB | `routes/auth.py` `routes/score.py` `db/` | FR-0, FR-26~31 + MariaDB·OAuth·시드 데이터 |
| **김관영** | 배달 분석 | `routes/delivery.py` `templates/delivery/` | FR-1~8 + Cloudtype 서버 |
| **이은석** | 시간 분석 | `routes/time.py` `templates/time/` | FR-9~15 + Cloudtype 배포 |
| **정재봉** | 종합 리포트 + 레포 관리 | `routes/report.py` `templates/report/` | FR-16~20 + 브랜치 전략·검수·머지 |
| **허남** | 히스토리 | `routes/history.py` `templates/history/` | FR-21~25 |
| **오영석** | AI 모듈 + 챌린지 | `ai/` `routes/challenge.py` `templates/challenge/` | FR-32~45 |

### 공통 규칙
- 페이지 라우트에 `@login_required` 유지
- AI 호출은 `try/except`로 감싸고 실패 시 수동 입력 fallback (FR-45)
- DB는 `db.client.db()`/`get_connection()`만 사용 (직접 `pymysql.connect()` 금지)
- 분석 저장 후 `services.score_service.recalculate_score(user_id)` 호출 (FR-31)
- `ai/` 함수 시그니처·반환 dict 형식은 docstring에 고정 — **형식 변경 시 팀 공지 필수**(다른 코드가 의존). 특히 `ai.comment.generate(type, context)`의 context 키는 라벨링 로직(#211)이 의존하므로 변경 금지

---

## 4. 협업 규칙

### 브랜치 전략
- `main` = 항상 동작하는 상태 유지. **main 직접 push 금지**
- 브랜치명: `feat/{영역}-{내용}` · `fix/{이슈}-{내용}` (예: `feat/delivery-ocr`, `fix/211-ai-comment-context`)
- 작업 흐름: 브랜치 생성 → 구현 → `pytest` PASS → PR(`Closes #N`) → **다른 팀원 1인 리뷰** → 머지

### 커밋 컨벤션
```
feat: 영수증 OCR 파싱 연동
fix: 시간 환산 0 입력 시 오류 수정
docs: README 역할 분담 갱신
chore: 의존성 추가
```

### 충돌 방지
- **자기 담당 파일만 수정** — `app.py`·`base.html`·`config.py`·`schema.sql` 등 공통 파일은 팀 합의 후
- `ai/` 함수 인터페이스(입출력 dict)·DB 스키마 변경은 **변경 전 공지** 필수
- 머지 순서: 인증/DB(김승현) → AI 모듈(오영석) → 각 도메인
- ⚠️ **stale base 주의**: 옛 base PR을 머지하면 최신 작업을 revert할 수 있음 → 충돌 해소 시 기능 커밋만 현재 main 위로 재적용

### 보안 (전원 필수)
- `.env` 절대 커밋 금지 — 키는 팀 채널로만 공유, 코드 하드코딩 금지
- 커밋 전 diff에 API 키·시크릿 포함 여부 확인
- 사용자 데이터 조회는 항상 본인 스코프 — 모든 쿼리에 `WHERE user_id=%s` 앱 레벨 필터 (RLS 제거됨, #21)

---

## 5. DB 전환 이력 (#22) — 트러블슈팅 참조

PR #22(`51be2ed`)로 main이 **Supabase → MariaDB**로 전환됨 (PRD §11 ERD 정합). 전환 전후로 작성된 코드/PR이 섞여 있어, 아래 항목에서 에러가 나면 "이전 → 현재" 기준으로 확인하세요.

| 영역 | 이전 (Supabase) | 현재 (MariaDB, #22~) |
|------|-----------------|----------------------|
| DB 접근 | `from db.client import get_supabase` · `get_supabase().table(...).select()...` | `from db.client import db` · `with db() as cursor: cursor.execute("... %s", (...))` |
| 의존성 | `supabase` | `pymysql` |
| env | `SUPABASE_URL` / `SUPABASE_KEY` / `SUPABASE_SERVICE_KEY` | `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` |
| 사용자 격리 | RLS(행 수준 보안) | 앱 레벨 — 모든 쿼리에 `WHERE user_id = %s` (#21) |
| 사용자 식별 | `auth.users`(Supabase Auth) | `users.(provider, provider_id)` upsert (#26) |
| 주차 경계 | `kst_bounds` → `+09:00` ISO 문자열 | `kst_bounds` → `"YYYY-MM-DD HH:MM:SS"`, DB 세션 TZ `+09:00` 고정 (#11) |
| 세션 | `session["user"]["id"]` | `session.get("user_id")` (falsy면 `abort(401)`) |

**자주 깨지는 지점**: ① `get_supabase` import 잔재 → `ImportError` ② 쿼리에 `WHERE user_id` 누락 → 타 사용자 데이터 노출 ③ `provider/provider_id` 미반영 브랜치 → `SELECT ... provider` SQL 에러 (#26 해결).

---

## 6. 배포 (Cloudtype)

- `main` push 시 `.github/workflows/deploy-main.yml`로 **자동 배포**(Secrets preflight 포함).
- 런타임: `Procfile` → `gunicorn app:app --workers 2 --timeout 120`. **멀티워커이므로** 주간 챌린지 정산 배치는 advisory lock으로 중복 실행을 차단한다(#206).
- 운영 마이그레이션(`db/migrations/001~004`)은 **수동 적용** 필요. 점수 의미 반전(#182) 배포 시 순서: 코드 배포 → `python -m scripts.backfill_scores` → `004_add_challenge_bonus_check.sql`.

---

## 7. 일정 가이드 (6~7일)

| Day | 목표 |
|-----|------|
| 1 | 환경 세팅 · MariaDB 스키마 적용 · OAuth 연동 · 점수 공식/상수 합의 |
| 2~4 | 도메인별 병렬 구현 (화면 → 로직 → AI 연동 → 저장) |
| 5 | 통합 테스트: 업로드→OCR→저장→히스토리→점수 전체 흐름 (PRD §9) |
| 6 | 데모 시나리오 완주 · 모바일(Chrome/Safari) QA · 시드 데이터·랭킹 확인 |
| 7 | 버퍼 · 발표 준비 |
