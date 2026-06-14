# 프로젝트 현황 — Dopamine Check

> 마지막 갱신: 2026-06-15

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
| MariaDB 인스턴스 프로비저닝 + 스키마 적용 | ⬜ 대기 | 김승현 |
| 시드 더미 데이터 20건 | ⬜ 대기 | 김승현 |

## 마지막 머지 PR

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

### Stitch 디자인 마이그레이션 (base.html 기준 → 각 페이지 적용)
- [x] login (#39) · [x] report (#51) · [x] delivery (#53) · [x] score (#50) · [x] time (#52)
- [ ] history · challenge — 각 담당이 `base.html` 상속 + Stitch 토큰으로 전환 (과도기 `style.css` 공존 중)

### P2 (통합 — Day 5~6)
- [ ] 전체 흐름 통합 테스트 · 데모 시나리오 완주 · 모바일 QA (Stitch 톤 혼재 페이지 시각 점검 포함)

## 알려진 이슈

| 이슈 | 내용 |
|------|------|
| #44 세션 쿠키 보안 | SameSite/Secure/HttpOnly 명시 설정 — ai:p2-followup |
| #43 413 핸들러 | MAX_CONTENT_LENGTH 초과 시 413 응답 + UX — ai:p2-followup |
| #42 CSRF DRY | challenge.py CSRF 로직을 utils/csrf.py로 통합 — ai:p2-followup |
| #24 챌린지 AI P2 잔존 | `calorie.py` kcal 스키마 검증·`next()` StopIteration 미처리 |
| #23 FR-35 race | 챌린지 중복참여 SELECT→INSERT race — 앱 검증만 적용, 커넥션 풀링과 함께 후속 |
| #11 주차 타임존(KST) | report 적용 완료, 타 도메인은 `utils/week.py` 공통 유틸 사용 권장 |
</content>
