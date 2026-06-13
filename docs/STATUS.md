# 프로젝트 현황 — Dopamine Check

> 마지막 갱신: 2026-06-13

## 인프라

| 항목 | 상태 | 담당 |
|------|------|------|
| GitHub 레포 (`luma-team-ai/dopacheck`) | ✅ 생성 | 정재봉 |
| DB MariaDB 전환 (#22, RLS→앱 레벨 `user_id` 필터) | ✅ 완료 | 정재봉 |
| `db/schema.sql` 작성 (MariaDB) | ✅ 완료 | 정재봉 |
| MariaDB 인스턴스 프로비저닝 + 스키마 적용 | ⬜ 대기 | 김승현 |
| Google / Kakao OAuth 연동 (#16 PR) | 🔄 진행 | 김승현 |
| Cloudtype 배포 | ⬜ 대기 | 김관영·이은석 |
| 시드 더미 데이터 20건 | ⬜ 대기 | 김승현 |

## 마지막 머지 PR

- #32 챌린지 AI P2 5건(#31 — LLM 타임아웃·CSRF·추천 캐시·인젝션 완화·avg_delivery) — 리뷰 P1(CSRF 빈 토큰) 픽스 후 머지
- #28 AI 모듈 + 챌린지(FR-32~38, 40~44, 오영석) — 검수 P1 2건 픽스(b4737c7) 후 머지, P2 후속 #31 분리
- #17 주차 공통 유틸 추출·#7 검증(정재봉) · #6 종합 리포트(FR-16~20, 정재봉) · #8·#12 히스토리 P2(허남) — PR머신 자동 머지

## 다음 작업

### P0 (구현 시작 최소 조건 — PRD §14)
- [ ] 도파민 점수 공식 팀 합의 (40/40/20)
- [ ] 환산 기준 상수값 확정 (config.py 초안 검토)
- [x] MariaDB 스키마 작성 (db/schema.sql, #22) — DB 인스턴스 적용은 인프라 표 참조
- [ ] OAuth 로그인 연동 (#16 PR 리뷰 대기 — #26 provider/provider_id 컬럼 선행)
- [ ] ⚠️ **배포 차단 게이트**: FLASK_SECRET_KEY 설정(#14) 완료 전 프로덕션 배포 금지 *(RLS 게이트는 #22 MariaDB 전환으로 폐기 — 앱 레벨 `user_id` 필터로 대체, #15 CLOSED)*

### P1 (도메인 구현 — 담당자별 병렬)
- [x] /report (정재봉, #6·#17) · [x] /history (허남, #3·#8·#12)
- [x] /challenge + ai/ (오영석, #28·#32) — AI 5종 + 챌린지, P2 보강 완료
- [ ] /delivery (김관영) · /time (이은석) · /score (김승현)
- [ ] 소셜 로그인 (김승현, #16 PR) — #26 provider/provider_id 컬럼 결정 대기(email UNIQUE 정책)

### P2 (통합 — Day 5~6)
- [ ] 전체 흐름 통합 테스트 · 데모 시나리오 완주 · 모바일 QA

## 알려진 이슈

| 이슈 | 내용 |
|------|------|
| #14 FLASK_SECRET_KEY 공개 기본값 | 운영 미설정 시 세션 위조 가능 — 배포 전 환경변수 필수 (김관영) |
| #26 provider/provider_id | 소셜로그인 식별키 컬럼 추가 + email UNIQUE 정책 결정 대기 (김승현) — #16 선행 |
| #24 챌린지 AI P2 잔존 | `calorie.py` kcal 스키마 검증·`next()` StopIteration 미처리 (avg_delivery·CSRF는 #32 해소) |
| #23 FR-35 race | 챌린지 중복참여 SELECT→INSERT race — 앱 검증만 적용, 커넥션 풀링과 함께 후속 |
| #11 주차 타임존(KST) | report 적용 완료, 타 도메인은 `utils/week.py` 공통 유틸 사용 권장 |
| #10 report 차트/SRI | 비교 차트 단위 정규화·CDN SRI — 프론트(Stitch) 재작업 시 (정재봉) |
