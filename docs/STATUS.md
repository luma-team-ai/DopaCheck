# 프로젝트 현황 — Dopamine Check

> 마지막 갱신: 2026-06-15

<a id="sprint"></a>
## 🎯 Ver1.2 마무리 스프린트 (D-2.5) — 역할 분배

> 발표까지 **약 2.5일**. P1 정합성·신규 기능은 **대부분 완료**, 남은 건 **시연 데이터·통합/모바일 QA·회귀 테스트**.
> 여기는 "지금 각자 뭘 해야 하나" 사람용 보드 — **코드 단위 작업은 GitHub 이슈**, 사람용 요약은 이 표로 본다.
> 우선순위: 🔴 P1(시연이 깨짐) > 🟡 P2 > ⚪ 조건부.

### ✅ 완료된 역할 항목 (2026-06-15 기준)
- **오영석**: #73 챌린지 완료 처리 ✅ · #74 join TOCTOU ✅ · #24 calorie 방어 ✅ (모두 CLOSED)
- **김승현**: `/admin` 통계 대시보드 ✅ (#106, 역할 재검증·이메일 마스킹 포함)
- **허남**: history·challenge **Stitch 마이그레이션 ✅** (`base.html` 상속, `style.css` 페이지 잔존 0) · 히스토리 상세 환산 항목 ✅ (#114→#127)
- **정재봉**: PRD Ver1.3 정합 ✅ (#109) · #76 score 시간지표 ✅ (#79) · 검수·머지 오케스트레이션(상시)

### ☐ 남은 작업 — 역할별 이슈 분배

| 담당 | 남은 일 (이슈) | 우선 | 근거 |
|------|---------------|------|------|
| **김승현** (DB) | ☐ **#131 랭킹/percentile 시연 더미 20건** — `db/seed.sql` 확장(users·records·scores) | 🔴 P1 | admin 랭킹·분포 화면 빈 상태, 시연 전제 |
| **이은석** (서버/프론트) | ☐ **#128 time `/analyze` CSRF 403 회귀 테스트** (test_time skip 해제) | 🟡 P2 | 회귀 방어 부재 |
| | ☐ **#130 모바일(Chrome/Safari) QA + 배포 안정화** | 🟡 P2 | PRD §9 |
| **김관영** (delivery) | ☐ **#129 통합 테스트 + OCR 정확도 QA 주도** — 업로드→OCR→저장→히스토리→점수 + 영수증 5종 | 🟡 P2 | PRD §9 |
| **오영석** (AI/챌린지) | ☐ **#60 챌린지 AI 비용절감·ID 검증 P2** (PR머신 후속) | 🟡 P2 | #59 후속 |
| **정재봉** (A/메타) | ☐ 통합 검수·PR 머지 오케스트레이션 · ~~#126 풀 타임아웃 DCL P2~~ ✅ (#132) | — | 상시 |

**Day별 흐름 (잔여)**
- **Day 1 (시연 데이터)**: 김승현 #131 seed 20건
- **Day 1.5~2 (안정화)**: 이은석 #128 CSRF 테스트 · 오영석 #60 챌린지 P2
- **Day 2~2.5 (통합)**: 김관영 #129 통합테스트·OCR QA · 이은석 #130 모바일 QA (전원 데모 완주)

## 인프라

| 항목 | 상태 | 담당 |
|------|------|------|
| GitHub 레포 (`luma-team-ai/dopacheck`) | ✅ 생성 | 정재봉 |
| Python 런타임 3.10.2 고정 (`runtime.txt`·`.python-version`) | ✅ 확정 | 정재봉 |
| DB MariaDB 전환 (#22, RLS→앱 레벨 `user_id` 필터) | ✅ 완료 | 정재봉 |
| `db/schema.sql` 작성 (MariaDB) | ✅ 완료 | 정재봉 |
| CloudType 자동배포 워크플로 (`deploy-main.yml`, push 시 배포 + Secrets preflight) | ✅ 완료·검증 | 정재봉 |
| **Stitch 디자인 기준 정립** (`base.html` 공통 디자인 시스템 — 팀원 상속 기준) | ✅ 완료 (#51) | 정재봉 |
| Tailwind Play CDN → PostCSS 빌드 전환 (`static/css/tailwind.css` 산출물 커밋, SRI 해소) | ✅ 완료 (#67) | 정재봉 |
| Google / Kakao OAuth 연동 (#16→#38 머지) | ✅ 완료 | 김승현 |
| MariaDB 인스턴스 프로비저닝 + 스키마 적용 | ✅ 완료 (Cloudtype) | 김승현 |
| 시드 더미 데이터 20건 (랭킹/percentile 시연) | ⬜ 대기 (**#131**) | 김승현 |
| 운영 마이그레이션 001~003 (role·challenges dedup·uc index) | ✅ 파일 머지 (운영 ALTER 적용 필요) | 김승현/정재봉 |

## 마지막 머지 PR

### 2026-06-15 배치 (정재봉 검수·머지)
- **#140** 리포트·챌린지·히스토리 레이아웃 공통(_app_base) 통일 (**#136 CLOSED**) — base.html 상속(자체 헤더·하단탭바 없음) → `_app_base.html`(공통 header+footer 탭바)로 전환. `_app_base` active_tab을 `default('delivery')`로 바꿔 라우트별 탭 강조 가능. report/challenge active_tab 전달, history(목록+상세) page_title 이전 + detail 삭제·뒤로가기를 본문 액션바로 이전(기능 보존). 브라우저 검증(4화면 헤더+탭바, 배달 회귀 없음, 상세 삭제 동작), worktree 전체 138 PASS. code-reviewer P1 0(P2/P3→후속 **#141**). G6 PASS. (작성 luma200ok→정재봉 머지)
- **#135** 챌린지 참여 400 복구 — challenges.id를 UUID(char36)로 처리 (**#133 CLOSED**) — **#119가 schema·코드를 BIGINT로 바꿨으나 운영 DB는 char(36) 그대로**라 모든 챌린지 '참여하기'가 400('잘못된 챌린지 ID') 전면 불능이던 회귀를 복구. `challenge.py` join `int()` 제거→UUID 문자열 검증(존재는 FK 보장), schema.sql CHAR(36) 복원. **운영 DB는 이미 char(36)→코드 pull만으로 복구(DB 작업 불필요)**. 브라우저 재현 201+DB INSERT 확인, 전체 138 PASS. code-reviewer P1 0(P2 3건→후속 **#134**). 메타 자체검수 G6 PASS
- **#132** `_resolve_pool_timeout` 동시성 테스트 캐시 격리 명시 (**#126 CLOSED**) — `test_concurrent_resolve_initializes_once` 진입 시 `_pool_timeout=None` 명시 초기화. autouse `reset_pool` fixture(#99)가 이미 리셋해 PR머신 지적은 실질 오탐이나, fixture 순서 비의존으로 견고화. 메타 자체검수 G1/G6 PASS, test_db_pool 24/24 PASS
- **#127** 히스토리 상세 환산 항목 렌더 추가 (**#114 CLOSED**) — `detail.html`에 헬스장 개월·강의 개·운동 회 렌더(라우트는 #112가 이미 계산). 메타 검수 G1/G6 PASS, history 테스트 17 PASS
  - 참고: 중복 stale PR **#121**은 이후 작성자가 머지(c9949a5) — 3-way 머지라 실질 반영분은 `.env.example` REDIRECT_URI 4줄뿐, 최근 작업 되돌림 없음(테스트 138 PASS 확인)
- **#125** user_challenges 복합 인덱스 운영 마이그레이션 003 추가 (**#123 CLOSED**) — `ALTER ... ADD INDEX IF NOT EXISTS idx_uc_user_challenge`. #120이 schema.sql만 바꿔 운영 미반영이던 것 보완. **운영 DB ALTER 수동 적용 필요**
- **#120** user_challenges 복합 인덱스(schema.sql) — FOR UPDATE gap lock 보장(#113 후속)
- **#106** 관리자 페이지 `/admin` 통계 대시보드 — admin_required 매요청 DB role 재검증 + 랭킹 이메일 마스킹 + 인가 테스트 4종(#106 P2 반영). code/security 인가 견고
- **#119** challenges/user_challenges id 타입 BIGINT AUTO_INCREMENT 정정 (**#115**) · **#122** PRD 스키마 정정 반영
- **#110** challenges 시드 중복(14→7) 제거 + title UNIQUE (**#97**) · **#103** 챌린지 TOCTOU 원자화·달성판정 (#73#74#88) · **#111** 챌린지 join FOR UPDATE
- **#124** `_resolve_pool_timeout` DCL 적용(#102) · **#116** 배달 빈파일 검증·수동입력 배달비 제외(#98#100) · **#117** SVG 파비콘 · **#109** PRD Ver1.3 정합

- #94 `DB_POOL_TIMEOUT` env 문서화 (**#71 CLOSED**, luma200ok 작성→PR머신 머지) — `.env.example`·README에 `DB_POOL_TIMEOUT`(기본30, 풀 소진 대기 한도 초과 시 503) 반영. 메타 자체검수·G6 PASS
- #92 커넥션 풀 bounded-timeout/503 (**#71 CLOSED**, luma200ok) — `db/client.py` `blocking=True` 무한대기 → `DB_POOL_TIMEOUT` 한도 후 503. gthread/eventlet 전환 대비 풀 고갈 안전화
- #86 delivery Top App Bar 화면별 페이지 제목 표시 (**#80**, 김관영)
- #90 마이페이지(`/mypage`) 화면 구현 + 기본 시급 설정 모달 (**FR-46~51**, 김승현) — 내 정보/이번주 점수/완료 챌린지 수/총 분석 횟수 표시 + `users.hourly_wage` 수정
- #87 AI `extract_text` 헬퍼 추가 + 모델 상수 중앙화 (**#20·#59 P2 CLOSED**, 오영석) — `ai/utils.py` 공통화
- #79 score 시간통계 평균→합계 + 게임 시간 포함 (**#76 P2 CLOSED**) — `routes/score.py` `SUM(youtube+instagram+tiktok+game)` (FR-31-1), 점수 산출값과 화면 표시 일치
- #89 report 비교차트 단일 dataset + recalc import 정리 (**#54·#83 CLOSED**, 정재봉) — miniChart 2-dataset null분리→단일 dataset `[lastVal,thisVal]`+바별 색상배열(BAR_LAST/THIS 보존, 0/null 모호·grouped 빈공간 해소) · `routes/report.py` recalc 지연import→모듈 최상위(순환 없음) · `tests/test_report.py` patch경로 `routes.report.recalculate_score`로 정정. 메타 자체검수(템플릿+import 정리, 서비스·레포 무관)·G6 PASS, pytest 117 PASS. #54 잔여 1건 완료(CDN/SRI는 #67 기완료)
- #81 CSRF DRY 통합 + 413 fallback + 세션쿠키 보안 (**#46/#42/#43/#44 해소**, Ketose333 작성→정재봉 사람검수 머지) — `history_delete`에 `verify_csrf()` 추가(P1: DELETE CSRF 누락) · `time.py` 로컬 CSRF 제거→공통 `utils/csrf.py` 통일(헤더 `X-CSRF-Token` OR 폼 `csrf_token` 둘 다 지원) · 413 핸들러 `BuildError`→'/' fallback · `SESSION_COOKIE_SECURE` 전용 env 분리(OR `FLASK_ENV=production`). code-reviewer P1 0 / security-reviewer P1 0, G6 PASS, pytest 115 PASS. **후속 P2**: time `/analyze` CSRF 미전송 403 테스트 부재(test_time 주요 케이스 skip 상태). 새 env `SESSION_COOKIE_SECURE` → `.env.example`·README 반영 완료
- #82 report 진입 시 점수 재산출 호출 추가 (**#75 P2 CLOSED**, 타 세션 머지) — report만 `recalculate_score` 미호출로 점수 stale 불일치 해소
- #84 헤더 프로필 아바타 드롭다운(마이페이지·로그아웃) 추가 (타 세션 머지)
- #77 delivery P2 3건 (**#55 CLOSED**, PR머신 생성→정재봉 사람검수 머지) — 업로드 오버레이 setInterval 정리(pageshow) · manual 폼 서버검증(빈 food_names·음수 total_price 거부) · `_stitch_head.html` Tailwind CDN 제거→정적 산출물. code-reviewer P1(z-[100]) **검증 결과 오탐**(빌드 내 실재+기존 코드), pytest 114 PASS. ⚠️ home/time/score CDN 잔존은 #67 후속(타 담당)
- #72 DBUtils 커넥션 풀 도입 (**#23 CLOSED**, 정재봉) — `db/client.py` 요청마다 `pymysql.connect()`→`PooledDB` 풀 전환(503/고갈 방지). 모듈 싱글톤 지연초기화+`threading.Lock` DCL, `db()` 외부 계약 유지, `DB_POOL_SIZE`(기본5). FR-35 중복검증은 기구현이라 범위 제외. reviewer P1 2건(`int("")` 방어·`blocking` 무한대기)→픽스+**#71 분리**, 재검토 APPROVE, pytest 111 PASS
- #70 홈 챌린지 집계를 `completed_at` 기준으로 통일 (**#69 P1 정합성 버그 CLOSED**, 정재봉) — `routes/home.py` 완료 집계가 `started_at`→`completed_at`로 score_service와 정합, `total`은 (시작 OR 완료) 합집합으로 확장해 completed ⊆ total 불변식 보장. code-reviewer P1 0건(초기 P1은 OR-COUNT 로직 정상 재분류), pytest 98 PASS
- #67 Tailwind Play CDN → PostCSS(v3 CLI) 빌드 전환 (#49 CLOSED, 정재봉) — `base.html`·`login.html` CDN 제거 → `static/css/tailwind.css` 산출물 커밋(SRI 해소). 인라인 config 컬러 47개 전량 이식. code-reviewer P1 3건 → **G3.5 원본 대조로 전부 무효**(orb 컨테이너 `z-[-1]`·인라인 opacity/스크롤 보존). main rebase 후 pytest 95 PASS
- #61 `recalculate_score`를 `services/score_service.py`로 분리 — **#58 CLOSED**(routes→routes 순환 임포트 제거, 계층 정리). #65 머지로 충돌 → main 리베이스 후 계산식은 #65 1:1 유지(동작 무변경). code-reviewer P1 2건(home.py 누락 import·테스트 patch 경로)→픽스 후 잔존 0, pytest 95 PASS
- #65 점수 계산식을 #48 합의(`config`/`ai.score.calculate`)로 통일 — **#62·#63 CLOSED**(score 점수식 회귀·time 입력폼 cosmetic 해소)
- #52 /time 시간 분석(입력폼·결과 Stitch UI + FR-9~15 파이프라인) — 이은석. time.py 충돌은 PR52 채택, base.html은 main Stitch + `{% block nav %}` 래핑(time만 nav 숨김), test DB mock 보강. code-reviewer APPROVE, **P2/P3 cosmetic 후속 #63**
- #50 홈 대시보드(헤더/푸터 공통 컴포넌트 + 실시간 데이터) + score Stitch UI — 김승현. score.py 충돌은 PR50 채택, test DB mock 보강(p1-blocked 해소). **점수식 회귀 → 후속 #62 분리**
- #53 delivery 영역 Stitch UI 적용(업로드/수동입력/결과 + 공통 앱셸) — 김관영
- #51 report 화면 Stitch 디자인 + 비교차트 정규화 + CDN SRI (#10 CLOSED, 정재봉) — code-reviewer P1 0건, P2-3은 후속 #49 분리
- #48 config 환산상수·도파민 점수공식 팀 합의 확정 (placeholder 경고 제거, 정재봉)
- #41 delivery CSRF + DRY + MAX_CONTENT_LENGTH · #40 FLASK_SECRET_KEY fallback 제거(#14) · #39 로그인 Stitch · #38 소셜 로그인(#16/#26)

## 다음 작업

### P0 (구현 시작 최소 조건 — PRD §14) — ✅ 전부 충족
- [x] 도파민 점수 공식 팀 합의 (40/40/20, #48 확정)
- [x] 환산 기준 상수값 확정 (`config.py`, #48)
- [x] MariaDB 스키마 작성 (db/schema.sql, #22) — DB 인스턴스 적용은 인프라 표 참조
- [x] OAuth 로그인 연동 (#38 머지)
- [x] 배포 차단 게이트 해제: FLASK_SECRET_KEY 설정(#14·#40) *(RLS 게이트는 #22로 폐기, #15 CLOSED)*

### P1 (도메인 구현 — 담당자별 병렬)
- [x] /report (정재봉, #6·#17·#51) · [x] /history (허남, #3·#8·#12)
- [x] /challenge + ai/ (오영석, #28·#32) · [x] /delivery (김관영, #35·#41·#53) · [x] 소셜 로그인 (김승현, #38)
- [x] /time (이은석, #52 머지) · [x] /score (김승현, #50·#65 — 점수식 #48 공식 통일 완료)

### Stitch 디자인 마이그레이션 (base.html 기준 → 각 페이지 적용) — ✅ 전 페이지 완료
- [x] login (#39) · [x] report (#51) · [x] delivery (#53) · [x] score (#50) · [x] time (#52)
- [x] history · [x] challenge — `base.html` 상속 전환 완료(페이지 템플릿 `style.css` 직접참조 0)

### P2 (통합 — Day 5~6)
- [ ] 전체 흐름 통합 테스트 · 데모 시나리오 완주 · 모바일 QA (Stitch 톤 혼재 페이지 시각 점검 포함)

## 알려진 이슈

| 이슈 | 내용 |
|------|------|
| ~~#73 챌린지 완료 처리 미구현~~ | ✅ **#103으로 해소** — 달성 판정·`is_completed`/`completed_at`/`progress` 쓰기 경로 구현, `challenge_bonus` 정상화 |
| ~~#74 챌린지 join TOCTOU~~ | ✅ **#103·#111·#120/#125로 해소** — join SELECT FOR UPDATE 원자화 + `(user_id,challenge_id)` 복합 인덱스(운영 003 적용 필요) |
| #131 랭킹 시연 더미 20건 | **P1** seed.sql에 랭킹/percentile 시연 데이터 미작성 → admin 화면 빈 상태 → 김승현 |
| #128 time CSRF 403 테스트 | **P2** time `/analyze` CSRF 미전송 403 회귀 테스트 부재(test_time skip) → 이은석 |
| #129 통합테스트·OCR QA | **P2** 전체 흐름 통합 + 영수증 5종 OCR 정확도 점검 → 김관영 |
| #130 모바일 QA·배포 안정화 | **P2** Chrome/Safari 모바일 시각/동작 QA + 배포 점검 → 이은석 |
| 운영 마이그레이션 적용 | 001~003 파일은 머지됨. **운영 Cloudtype DB에 ALTER 수동 실행 필요**(특히 003 인덱스 → #113 TOCTOU 발효 조건) |
| ~~#75 report 점수 재산출 누락~~ | ✅ **#82로 해소** — report 진입 시 `recalculate_score` 호출 추가 |
| ~~#76 score 시간지표 불일치~~ | ✅ **#79로 해소** — score 시간통계 game 포함 SUM으로 변경, 점수 산출값과 일치 (FR-31-1) |
| ~~#44/#43/#42 (CSRF DRY·413·세션쿠키)~~ | ✅ **#81로 해소** — CSRF 전 도메인 `utils/csrf.py` 통일(challenge·delivery·time·history), 413 BuildError fallback, `SESSION_COOKIE_SECURE` env 분리 |
| #46후속 time CSRF 테스트 | **P2** time `/analyze` CSRF 미전송 403 회귀 테스트 부재(test_time 주요 케이스 skip 상태) → 이은석 |
| #24 챌린지 AI P2 잔존 | `calorie.py` kcal 스키마 검증·`next()` StopIteration 미처리 |
| (FR-35 race → #74로 승격) | 무결성검사로 '두 트랜잭션 분리'까지 확인되어 전용 이슈 #74 등록 |
| ~~#71 풀 blocking 무한대기~~ | ✅ **#92·#94로 해소** — `DB_POOL_TIMEOUT`(기본30) bounded-timeout/503 적용, gthread 전환 안전화 |
| #11 주차 타임존(KST) | report 적용 완료, 타 도메인은 `utils/week.py` 공통 유틸 사용 권장 |
</content>
