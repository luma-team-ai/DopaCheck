# PRD — 도파민 대리 만족 (Dopamine Check)

> AI 심화 과정 팀 프로젝트 | 6인 팀 | 개발 기간: 6~7일  
> 작성일: 2026-06-11 (Ver1.1) / 갱신일: 2026-06-15 (Ver1.3)  
> 팀원: 김승현(DB담당), 김관영(Flask/백엔드), 이은석(서버세팅/프론트), 정재봉(리포트), 허남(히스토리), 오영석(AI모듈/챌린지)
>
> 📋 진행 현황·팀원별 할 일은 [docs/STATUS.md](STATUS.md) 참조

---

## 0-1. Ver1.3 변경 요약 (2026-06-15 — 실제 코드 정합)

Ver1.2 문서와 실제 구현 간 불일치를 코드 기준으로 정정했다.

- **AI 모델명 정정**: `claude-sonnet-4-20250514` → 실제 `claude-haiku-4-5` (`config.py` 기준, OCR·칼로리·코멘트·챌린지 전부 동일 모델)
- **`DB_POOL_TIMEOUT` 환경변수 추가**: 커넥션 풀 소진 대기 한도(초, 기본 30) 초과 시 503 반환 (#71→#92·#94). gthread/eventlet 워커 전환 대비 무한대기 제거
- **챌린지 달성/보너스 상태 정정**: FR-38(달성 시 +5점) 및 §8 수용기준을 **미구현(#73)** 으로 표기. `is_completed`/`completed_at`/`progress` 쓰기 경로가 없어 `challenge_bonus`가 구조적으로 항상 0 — 발표 전 구현 필요
- **score 시간통계(FR-31-1) 구현 확인**: 코드상 이미 game 포함 주간 SUM 반영(`routes/score.py`, #79). Ver1.2 표기가 정확함을 확인
- **PRD 파일을 repo로 이동**: `docs/PRD.md`로 편입(버전관리·팀 공유)

---

## 0. Ver1.2 변경 요약

Ver1.1(2026-06-11) 작성 이후 실제 구현 진행에 따라 아래 항목이 변경/추가되었다.

- **신규 화면**: 마이페이지 (`/mypage`) — 사용자 정보·이번 주 점수·완료 챌린지 수·총 분석 횟수 조회, 기본 시급 설정 모달
- **헤더 개편**: 프로필 아바타 클릭 시 마이페이지·로그아웃 드롭다운 메뉴 추가
- **AI 점수 산출 모듈 위치 변경**: `ai/score.py` 산출 로직을 `services/score_service.py`(`recalculate_score`)로 분리, 배달/시간/챌린지 라우트 저장 직후 공통 호출
- **점수 화면 시간 통계 수정**: `/score`의 시간 통계를 "평균"이 아닌 "이번 주 합계" 기준으로 통일하고 게임 시간(`game_min`)을 포함 (FR-26~31 일관성 확보)
- **리포트 점수 재산출 보강**: `/report` 진입 시에도 `recalculate_score` 호출 추가
- **DB 커넥션 풀 도입**: `db/client.py`에 `DBUtils.PooledDB` 적용 (`DB_POOL_SIZE` 환경변수)
- **users 테이블 스키마 변경**: `provider`(google/kakao), `provider_id` 컬럼 추가 — `(provider, provider_id)` UNIQUE 기반 upsert로 소셜 로그인 사용자 식별
- **CSRF/보안 보강**: history DELETE·time 분석 요청에 CSRF 토큰 적용, 413(업로드 용량 초과) 에러 핸들러 추가, `SESSION_COOKIE_SECURE` 환경변수 분리
- **카카오 OAuth scope에 `profile_image` 추가**
- **Tailwind CSS**: Play CDN → PostCSS 빌드 전환 (배포 시 빌드 스텝 필요)
- **공통 컴포넌트**: delivery 등 주요 화면에 앱셸 공통 header/footer 컴포넌트 적용
- **유틸 패키지 추가**: `utils/week.py`(주차 범위 계산), `utils/csrf.py`(CSRF 토큰 검증 공통화)
- **관리자 페이지 신규 추가 (예정)**: `users.role`(user/admin) 컬럼 추가, `role='admin'` 계정 로그인 시 `/admin`으로 자동 리다이렉트, 비관리자가 `/admin` 접근 시 홈(`/`)으로 리다이렉트. 가입자/활성 사용자 수, 배달·시간 분석 건수·합계, 도파민 점수 분포(평균/최고/최저/랭킹), 챌린지 참여·완료 통계를 표시하는 통계 대시보드

---

## 1. 배경

- **현재 문제:**  
  사람들은 배달 앱 주문, SNS, 유튜브, 게임 등 즉각적인 도파민 자극 소비에 익숙해져 있으나, 자신이 얼마나 많은 돈과 시간을 소비하는지 체감하지 못한다. 소비 행위 자체가 무의식적으로 이루어지기 때문에 반성이나 변화의 계기를 갖기 어렵다.

- **왜 지금 필요한가:**  
  배달 앱 사용량 및 스마트폰 평균 사용 시간이 꾸준히 증가하고 있으며, MZ세대를 중심으로 소비 패턴에 대한 자기 인식 요구가 높아지고 있다. 데이터 시각화와 AI 기반 인사이트를 통해 "대리 만족"이라는 심리적 각성 효과를 제공하는 서비스가 필요하다.

- **관련 문서/이슈:**
  - 기술 스택: Flask, Jinja2, MariaDB, Cloudtype
  - AI 모듈: OCR(영수증 파싱), LLM(칼로리 추론·공감 코멘트·챌린지 추천·점수 산출)
  - 오영석 담당 AI 서비스 모듈 — Flask 앱 내부 모듈로 통합 (ai/ 패키지)
  - 점수 재산출 공통 로직은 `services/score_service.py`로 분리되어 각 라우트(배달/시간/챌린지/리포트)에서 호출됨 (Ver1.2)

---

## 2. 목표

- **사용자가 무엇을 할 수 있어야 하는가:**
  1. 배달 영수증을 업로드하면 지출 금액·칼로리를 자동 분석하고, "치킨 N마리값", "러닝 N분" 등으로 환산된 결과를 확인할 수 있다.
  2. SNS·유튜브·게임 사용 시간을 입력하면 "책 N권", "시급 N원짜리 취미" 등으로 환산된 시간 소비 리포트를 확인할 수 있다.
  3. 종합 도파민 점수와 히스토리를 통해 자신의 소비 패턴 변화를 추적할 수 있다.
  4. AI가 추천한 챌린지에 참여해 소비 습관 개선 목표를 설정하고 달성률을 확인할 수 있다.
  5. **(Ver1.2 신규)** 마이페이지에서 내 정보(닉네임·이메일·가입일), 이번 주 점수, 완료 챌린지 수, 총 분석 횟수를 확인하고 기본 시급을 수정할 수 있다.

- **비즈니스 또는 운영상 기대 효과:**
  - AI 심화 과정 발표에서 OCR·LLM·데이터 시각화를 실제 서비스에 통합한 사례로 시연
  - 사용자에게 소비 패턴에 대한 자기 인식(각성)과 공감을 동시에 제공

---

## 3. 대상 사용자

- **주요 사용자:** 배달 앱과 SNS를 자주 이용하는 20~30대. 자신의 소비 패턴을 돌아보고 싶지만 번거로운 기록은 하고 싶지 않은 사람.
- **보조 사용자:** AI 심화 과정 강사 및 수강생 (발표 청중)
- **관리자 또는 운영자 영향:** `users.role='admin'` 계정으로 로그인하면 `/admin` 통계 대시보드에서 가입자·분석·점수·챌린지 현황을 조회할 수 있다. (Ver1.2 추가)

---

## 4. 범위

이번 작업에 포함:

- [x] 소셜 로그인 (Google / Kakao) — 모든 기능 로그인 필수, 비로그인 접근 불가
- [x] 배달 영수증 OCR 파싱 및 분석 (`/delivery`) — 김관영 (Flask 담당)
- [x] 시간 소비 입력 및 환산 분석 (`/time`) — 이은석 (서버 세팅 + 프론트)
- [x] 종합 리포트 + SNS 공유 카드 (`/report`) — 정재봉
- [x] 분석 히스토리 조회 및 삭제 (`/history`) — 허남
- [x] 도파민 점수 산출 및 랭킹 (`/score`) — 김승현 (DB 담당)
- [x] AI 챌린지 추천 및 참여 (`/challenge`) — 오영석
- [x] AI 서비스 모듈 (OCR, LLM 칼로리 추론, 공감 코멘트, 점수 산출) — 오영석, Flask 내부 모듈 (ai/ 패키지)
- [x] **(Ver1.2 신규)** 마이페이지 (`/mypage`) — 내 정보·점수·챌린지·분석 횟수 조회, 기본 시급 설정 — 김승현
- [ ] **(Ver1.2 신규, 예정)** 관리자 페이지 (`/admin`) — `role='admin'` 계정 전용 통계 대시보드 — 김승현

이번 작업에 포함하지 않음:

- [ ] 푸시 알림 / 이메일 알림
- [ ] 모바일 앱 (iOS/Android 네이티브)
- [ ] 유튜브 Google Takeout CSV 업로드 (시간 허용 시 추가)
- [ ] 소셜 기능 (친구 추가, 피드)
- [ ] 비로그인 체험 모드

---

## 5. 사용자 흐름

### 흐름 A — 배달 분석
1. 사용자가 로그인 후 `/delivery` 에 접속해 배달 영수증 이미지를 업로드한다.
2. AI 모듈(OCR)이 음식명·금액·배달비를 추출하고, LLM이 칼로리를 추론한다.
3. 사용자는 추출 결과를 확인하고 필요 시 수동 수정한다.
4. 시스템이 지출 환산("치킨 N마리"), 칼로리 환산("러닝 N분"), LLM 공감 코멘트를 화면에 표시한다.
5. 결과가 MariaDB(Cloudtype)에 저장되고 히스토리·도파민 점수(`recalculate_score`)에 즉시 반영된다.

### 흐름 B — 시간 시각화
1. 사용자가 로그인 후 `/time` 에 접속해 앱별 주간 사용 시간(시간 단위)과 시급을 입력한다.
2. AI 모듈이 시간 환산("책 N권", "시급 N원짜리 취미")과 LLM 공감 코멘트를 반환한다.
3. 시스템이 도넛 차트와 환산 결과를 화면에 표시한다.
4. 결과가 MariaDB(Cloudtype)에 저장되고 히스토리·도파민 점수(`recalculate_score`)에 즉시 반영된다.

### 흐름 C — 챌린지
1. 사용자가 로그인 후 `/challenge` 에 접속하면 AI가 히스토리 기반 맞춤 챌린지를 추천한다.
2. 사용자가 챌린지를 선택하고 목표를 설정한다.
3. 이후 배달/시간 분석 결과가 쌓이면 달성률이 자동 업데이트된다.
4. 챌린지 달성 시 도파민 점수에 보너스(+5점)가 반영된다.

### 흐름 D — 비로그인 접근
1. 비로그인 사용자가 임의의 URL에 접근한다.
2. 시스템이 `/login` 으로 즉시 리다이렉트한다.

### 흐름 E — 마이페이지 (Ver1.2 신규)
1. 사용자가 로그인 후 헤더의 프로필 아바타를 클릭하면 마이페이지·로그아웃 드롭다운이 표시된다.
2. 마이페이지로 진입하면 닉네임·이메일(카카오 소셜 회원은 "카카오 소셜 회원"으로 표기)·가입일·이번 주 도파민 점수·완료 챌린지 수·총 분석 횟수(배달+시간)가 표시된다.
3. 사용자가 기본 시급 설정 모달을 열어 새 시급(양의 정수)을 입력하고 저장하면 `users.hourly_wage`가 갱신된다.
4. 저장 성공/실패 시 flash 메시지로 결과를 안내한다.

### 흐름 F — 관리자 통계 대시보드 (Ver1.2 신규, 예정)
1. `users.role='admin'`인 사용자가 소셜 로그인을 완료하면, 시스템은 일반 홈이 아닌 `/admin`으로 즉시 리다이렉트한다.
2. `/admin`은 가입자/활성 사용자 수, 배달·시간 분석 건수 및 합계, 도파민 점수 분포(평균/최고/최저, 랭킹), 챌린지 참여·완료 통계를 카드/표 형태로 표시한다.
3. `role='user'`인 일반 사용자가 `/admin` URL에 직접 접근하면 홈(`/`)으로 리다이렉트되며, 별도 에러 메시지는 표시하지 않는다.

---

## 6. 기능 요구사항

### 공통 인증 (김승현 — DB / 김관영 — Flask)
- FR-0: 모든 페이지는 로그인 상태를 확인하며, 비로그인 사용자는 `/login`으로 리다이렉트한다.
- FR-0-1: 사용자는 Google 또는 Kakao 소셜 로그인으로 가입/로그인할 수 있어야 한다.
- FR-0-2 **(Ver1.2)**: 소셜 로그인 사용자는 `(provider, provider_id)` UNIQUE 기준으로 upsert되며, 재로그인 시 닉네임이 갱신된다. 카카오 로그인은 `profile_image` scope를 포함한다.
- FR-0-3 **(Ver1.2 신규, 예정)**: 로그인 완료 시 `users.role`을 조회하여 `role='admin'`이면 `/admin`으로, 그 외(`user`)는 기존과 동일하게 홈으로 리다이렉트한다.

### 배달 분석 (`/delivery` — 김관영)
- FR-1: 사용자는 JPG·PNG 형식의 영수증 이미지를 업로드할 수 있어야 한다.
- FR-2: OCR AI 모듈은 음식명·단가·수량·배달비를 추출해야 한다.
- FR-3: LLM AI 모듈은 추출된 음식명을 기반으로 칼로리(kcal)를 추론해야 한다.
- FR-4: 시스템은 총 지출을 "치킨 N마리 / 헬스장 N개월" 단위로 환산해야 한다.
- FR-5: 시스템은 총 칼로리를 "러닝 N분 / 걷기 N시간" 단위로 환산해야 한다.
- FR-6: LLM은 분석 결과 기반 공감 코멘트를 생성해야 한다.
- FR-7: OCR 파싱 실패 시 사용자에게 수동 입력 폼(fallback)을 제공해야 한다.
- FR-8: 분석 결과는 MariaDB에 저장되고 히스토리·점수에 즉시 반영되어야 한다.
- FR-8-1 **(Ver1.2)**: 업로드 파일 크기가 5MB(`MAX_CONTENT_LENGTH`)를 초과하면 413 에러를 안내 메시지와 함께 `/delivery`로 리다이렉트한다.

### 시간 시각화 (`/time` — 이은석, 서버 세팅 포함)
- FR-9: 사용자는 유튜브·인스타·틱톡·게임별 주간 사용 시간을 시간(h) 단위로 입력할 수 있어야 한다.
- FR-10: 사용자는 시급(원)을 입력할 수 있어야 한다.
- FR-11: 시스템은 SNS 시간을 "책 N권 / 강의 N개 / 운동 N회"로 환산해야 한다.
- FR-12: 시스템은 게임 시간을 "시급 기준 N원짜리 취미"로 환산해야 한다.
- FR-13: 시스템은 앱별 사용 시간 비율 도넛 차트를 렌더링해야 한다.
- FR-14: LLM은 분석 결과 기반 공감 코멘트를 생성해야 한다.
- FR-15: 분석 결과는 MariaDB에 저장되고 히스토리·점수에 즉시 반영되어야 한다.
- FR-15-1 **(Ver1.2)**: 분석 요청은 CSRF 토큰 검증을 거쳐야 한다.

### 종합 리포트 (`/report` — 정재봉)
- FR-16: 시스템은 배달 지출·시간 소비 통합 대시보드를 표시해야 한다.
- FR-17: LLM은 종합 인사이트 코멘트를 생성해야 한다.
- FR-18: 시스템은 도파민 점수를 표시해야 한다.
- FR-19: 사용자는 결과 카드를 이미지로 저장하거나 SNS 공유할 수 있다. (html2canvas 활용)
- FR-20: 저번 주 vs 이번 주 비교 차트를 표시해야 한다. (추가 기능)
- FR-20-1 **(Ver1.2)**: `/report` 진입 시 `recalculate_score`를 호출해 최신 데이터 기준으로 점수를 재산출한 뒤 표시한다.

### 히스토리 (`/history` — 허남)
- FR-21: 사용자는 날짜별 분석 기록 목록을 조회할 수 있어야 한다.
- FR-22: 사용자는 특정 기록의 상세 내용을 조회할 수 있어야 한다.
- FR-23: 사용자는 기록을 삭제할 수 있어야 한다.
- FR-23-1 **(Ver1.2)**: 기록 삭제(DELETE) 요청은 CSRF 토큰 검증을 거쳐야 한다.
- FR-24: 사용자는 이번 주 / 이번 달 / 전체 기간 필터를 적용할 수 있어야 한다.
- FR-25: 같은 날 동일 유형 분석을 여러 번 하면 누적 저장된다. (덮어쓰기 없음)

### 도파민 점수 (`/score` — 김승현)
- FR-26: 시스템은 배달·시간 데이터를 기반으로 도파민 점수(0~100)를 산출해야 한다. **(Ver1.2: 산출 함수는 `services/score_service.recalculate_score`로 구현, 배달/시간/챌린지/리포트 저장·조회 시점에 upsert)**
- FR-27: 점수 산출 공식: `배달 기여(40%) + 시간 기여(40%) + 챌린지 보너스(20%)`
- FR-28: 시스템은 점수 구성 항목별 기여도를 시각화해야 한다.
- FR-29: 시스템은 전체 사용자 평균 대비 내 점수를 표시해야 한다.
- FR-30: 시스템은 상위 N% 랭킹을 표시해야 한다. (시드 더미 데이터 20건 이상 사전 삽입)
- FR-31: 새 분석 결과 저장 시 도파민 점수를 즉시 재산출(upsert)해야 한다.
- FR-31-1 **(Ver1.2)**: `/score` 화면의 "이번 주 사용 시간" 통계는 `youtube_min + instagram_min + tiktok_min + game_min`의 **주간 합계(SUM)** 기준으로 산출하며, 점수 산출(`recalculate_score`)과 동일한 값을 사용한다. (변경 전: 게임 제외 + 레코드 평균(AVG) — 점수와 화면 표시값 불일치 버그 수정)

### 챌린지 (`/challenge` — 오영석)
- FR-32: 시스템은 기본 챌린지 목록을 제공해야 한다. (예: "이번 주 배달 3회 이하", "SNS 하루 1시간 이하")
- FR-33: AI 모듈은 사용자 히스토리 기반 맞춤 챌린지를 추천해야 한다.
- FR-34: 사용자는 챌린지를 선택하고 목표를 설정할 수 있어야 한다.
- FR-35: 동일 챌린지는 활성 상태에서 중복 참여 불가하다.
- FR-36: 시스템은 챌린지 달성률 프로그레스 바를 표시해야 한다.
- FR-37: 챌린지 달성 판정은 분석 결과 저장 시 실시간 트리거 방식으로 처리한다. **(Ver1.2: 홈 챌린지 집계는 `completed_at` 기준으로 통일)**
- FR-38: 챌린지 달성 시 도파민 점수에 +5점 보너스가 반영되어야 한다. **(Ver1.3: 미구현 #73 — `is_completed`/`completed_at`/`progress` 쓰기 경로 추가 필요, 현재 `challenge_bonus` 구조적 0)**

### 마이페이지 (`/mypage` — Ver1.2 신규, 김승현)
- FR-46: 사용자는 마이페이지에서 닉네임, 이메일(카카오 소셜 회원은 "카카오 소셜 회원"으로 표시), 가입일을 조회할 수 있어야 한다.
- FR-47: 마이페이지는 이번 주(KST, 월요일 시작) 도파민 점수를 표시해야 한다. 점수 기록이 없으면 0으로 표시한다.
- FR-48: 마이페이지는 완료된 챌린지 수(`is_completed=1` 누적)를 표시해야 한다.
- FR-49: 마이페이지는 총 분석 횟수(배달 분석 건수 + 시간 분석 건수)를 표시해야 한다.
- FR-50: 사용자는 기본 시급(`users.hourly_wage`)을 모달을 통해 수정할 수 있어야 한다. 입력값은 0 이상의 정수여야 하며, 미입력·음수·정수 변환 실패 시 에러 flash와 함께 저장을 거부한다.
- FR-51: 헤더의 프로필 아바타를 클릭하면 마이페이지 이동·로그아웃 메뉴를 포함한 드롭다운이 표시되어야 한다.

### 관리자 (`/admin` — Ver1.2 신규, 예정, 김승현)
- FR-52: `users.role` 컬럼(`user`/`admin`, 기본값 `user`)으로 관리자 여부를 식별한다. 관리자 지정은 DB 직접 수정(Cloudtype 콘솔)으로 처리하며 별도 UI는 제공하지 않는다.
- FR-53: `role='admin'` 계정으로 로그인하면 즉시 `/admin`으로 리다이렉트한다. (FR-0-3)
- FR-54: `/admin`은 `admin_required` 가드를 통과한 요청만 처리하며, `role='user'`가 접근하면 홈(`/`)으로 리다이렉트한다.
- FR-55: `/admin`은 전체 가입자 수와 최근 N일 내 분석 기록(배달 또는 시간)이 있는 활성 사용자 수를 표시해야 한다.
- FR-56: `/admin`은 전체 배달·시간 분석 건수와 총 지출 금액·총 사용 시간(분)을 표시해야 한다.
- FR-57: `/admin`은 `dopamine_scores` 기준 전체 사용자 점수의 평균/최고/최저값과 상위 랭킹 목록을 표시해야 한다.
- FR-58: `/admin`은 `user_challenges` 기준 전체 참여 수와 완료 수(완료율)를 표시해야 한다.

### AI 서비스 모듈 (오영석 — 별도 API 서버)
- FR-39: AI 모듈은 Flask 앱 내부 패키지(ai/)로 통합되며, 각 라우트에서 직접 함수 호출 방식으로 사용한다.
- FR-40: `ai.ocr.parse_receipt(image_bytes)` — 이미지 바이트를 입력받아 구조화된 dict 반환
- FR-41: `ai.calorie.estimate(items)` — 음식명 배열을 입력받아 kcal dict 반환
- FR-42: `ai.comment.generate(type, context)` — 분석 컨텍스트를 입력받아 공감 코멘트 문자열 반환
- FR-43: `ai.score.calculate(data)` — 배달·시간 데이터를 입력받아 점수 dict 반환. **(Ver1.2: 점수 재산출·저장(upsert) 오케스트레이션은 `services/score_service.recalculate_score`가 담당하며, 이 함수가 각 라우트에서 공통 호출된다.)**
- FR-44: `ai.challenge.recommend(history)` — 히스토리 데이터를 입력받아 추천 챌린지 목록 반환

- FR-45: AI 모듈 함수 호출 실패 시 예외를 catch하여 사용자에게 에러 메시지와 수동 입력 fallback을 제공해야 한다.

---

## 7. 비기능 요구사항

- **성능:**
  - OCR 처리 응답 시간 10초 이내
  - LLM 코멘트 응답 시간 5초 이내
  - 일반 페이지 로딩 2초 이내
  - AI 처리 중 로딩 스피너 + 단계별 진행 메시지 표시 필수

- **접근성:** 모바일 브라우저(Chrome, Safari)에서 정상 동작해야 한다.

- **보안:**
  - 모든 페이지 로그인 필수, 비로그인 접근 시 `/login` 리다이렉트
  - Flask 세션 기반 인증 + MariaDB 쿼리 시 user_id 필터 필수 적용 — 본인 데이터만 조회 가능
  - AI 모듈 API 키는 환경변수(.env)로 관리, 코드에 하드코딩 금지
  - **(Ver1.2)** 세션 쿠키는 `HTTPONLY=True`, `SAMESITE=Lax`로 설정하며, `SECURE` 속성은 `SESSION_COOKIE_SECURE` 환경변수(또는 `FLASK_ENV=production`)로 운영/개발 분리한다.
  - **(Ver1.2)** 상태 변경 요청(history DELETE, time 분석 등)은 CSRF 토큰 검증(`utils/csrf.py`)을 거친다.

- **로깅/모니터링:**
  - AI 모듈 API 호출 실패 시 에러 로그 기록
  - Cloudtype 서버 에러 로그 수집

---

## 8. 수용 기준

### 인증
- [x] Given 비로그인 사용자가, When 어떤 페이지에 접근하더라도, Then 로그인 페이지(`/login`)로 리다이렉트된다.
- [x] Given 사용자가, When Google/Kakao 소셜 로그인을 완료하면, Then 홈 화면으로 이동한다.

### 배달 분석
- [x] Given 로그인한 사용자가, When 영수증 이미지를 업로드하면, Then OCR이 음식명과 금액을 추출하여 화면에 표시한다.
- [x] Given OCR 추출 결과가 있을 때, When 사용자가 수정 후 확인하면, Then 수정된 값 기준으로 칼로리·환산 결과가 계산된다.
- [x] Given OCR 파싱에 실패하면, Then 수동 입력 폼이 표시된다.
- [x] Given 분석이 완료되면, When 결과 화면이 표시될 때, Then LLM 공감 코멘트가 함께 출력된다.
- [x] Given 분석이 완료되면, Then 결과가 MariaDB에 저장되고 히스토리에서 조회된다.
- [x] Given 업로드 파일이 5MB를 초과하면, Then 안내 메시지와 함께 `/delivery`로 리다이렉트된다. (Ver1.2)

### 시간 시각화
- [x] Given 로그인한 사용자가, When 앱별 시간(h)과 시급을 입력하면, Then 환산 결과와 도넛 차트가 표시된다.
- [x] Given 시간 분석이 완료되면, Then 결과가 MariaDB에 저장되고 히스토리에서 조회된다.

### 도파민 점수
- [x] Given 배달 또는 시간 분석이 저장되면, Then 도파민 점수가 즉시 재산출되어 `/score`에 반영된다.
- [x] Given 사용자가 `/score`에 접속하면, Then 점수·항목별 기여도·상위 N% 랭킹이 표시된다.
- [x] Given 사용자가 `/score`에 접속하면, Then "이번 주 사용 시간"은 게임 시간을 포함한 주간 합계로 표시되며 점수 산출 값과 일치한다. (Ver1.2)

### 챌린지
- [x] Given 히스토리 데이터가 1건 이상 있을 때, When 챌린지 페이지에 접속하면, Then AI 맞춤 추천 챌린지가 표시된다.
- [x] Given 동일 챌린지가 이미 활성 상태일 때, When 다시 참여를 시도하면, Then 중복 참여가 차단된다.
- [ ] Given 챌린지를 달성하면, Then 도파민 점수에 +5점 보너스가 반영된다. **(Ver1.3: 미구현 — #73, 완료 쓰기 경로 부재로 `challenge_bonus` 항상 0)**

### 마이페이지 (Ver1.2 신규)
- [x] Given 로그인한 사용자가, When 헤더의 프로필 아바타를 클릭하면, Then 마이페이지·로그아웃 드롭다운이 표시된다.
- [x] Given 사용자가 `/mypage`에 접속하면, Then 닉네임/이메일/가입일/이번 주 점수/완료 챌린지 수/총 분석 횟수가 표시된다.
- [x] Given 사용자가 기본 시급 모달에 양의 정수를 입력하고 저장하면, Then `users.hourly_wage`가 갱신되고 성공 flash가 표시된다.
- [x] Given 사용자가 시급 입력값을 비우거나 음수/비정수로 입력하면, Then 저장이 거부되고 에러 flash가 표시된다.

### 관리자 (Ver1.2 신규, 예정)
- [ ] Given `role='admin'` 계정이, When 소셜 로그인을 완료하면, Then `/admin`으로 리다이렉트된다.
- [ ] Given `role='user'` 계정이, When `/admin` URL에 직접 접근하면, Then 홈(`/`)으로 리다이렉트된다.
- [ ] Given 관리자가 `/admin`에 접속하면, Then 가입자/활성 사용자 수, 배달·시간 분석 건수·합계, 점수 평균/최고/최저 및 랭킹, 챌린지 참여·완료 통계가 표시된다.

### AI 모듈
- [x] Given AI 모듈 API 호출이 실패하면, Then 사용자에게 에러 메시지가 표시되고 수동 입력 fallback이 제공된다.
- [x] Given 타 도메인에서 AI 모듈 API를 호출하면, Then CORS 오류 없이 정상 응답한다. (Flask 내부 모듈 통합으로 해당 없음)

---

## 9. 검증 계획

- **단위 테스트:**
  - AI 모듈: 샘플 영수증 5종(배달의민족·쿠팡이츠) OCR 파싱 정확도 — 음식명·금액 추출 성공률 80% 이상 목표
  - 환산 로직: 칼로리→운동, 지출→대체재, 시간→대체활동 함수 경계값(0, 음수, 매우 큰 값) 테스트
  - 도파민 점수 산출 함수(`services/score_service.recalculate_score`) 입력/출력 검증
  - **(Ver1.2)** `tests/test_score.py`, `tests/test_report.py`, `tests/test_history.py`, `tests/test_challenge.py` — pytest 기반 라우트/계산 단위 테스트

- **통합 테스트:**
  - 영수증 업로드 → OCR → LLM 칼로리 추론 → DB 저장 → 히스토리 조회 → 점수 반영 전체 흐름 (Day 5)
  - 시간 입력 → 환산 → DB 저장 → 히스토리 조회 → 점수 반영 전체 흐름 (Day 5)
  - 챌린지 참여 → 분석 저장 → 달성 판정 → 점수 보너스 반영 흐름 (Day 5)
  - **(Ver1.2)** 마이페이지 시급 수정 → `/time` 분석 시 적용 흐름 확인

- **수동 확인:**
  - 발표 시연용 데모 시나리오 전체 흐름 1회 완주 (Day 6)
  - 모바일 브라우저(Chrome, Safari) UI 확인
  - 로그인/로그아웃 및 user_id 기반 데이터 격리 확인
  - 시드 더미 데이터 기반 랭킹 정상 표시 확인

---

## 10. 리스크와 열린 질문

- **리스크:**
  - OCR 정확도: 배달 영수증 레이아웃이 앱마다 달라 파싱 실패 가능 → 수동 수정 fallback 필수
  - LLM 응답 지연: 공감 코멘트 생성이 5초 이상 걸릴 경우 UX 저하 → 로딩 스피너 + 타임아웃 처리 필요
  - MariaDB 쿼리 시 user_id 필터 누락 시 타 사용자 데이터 노출 위험 → 모든 쿼리에 WHERE user_id = ? 필수
  - AI 모듈이 Flask 내부 모듈로 통합되어 CORS 이슈 없음 (동일 서비스)
  - 6~7일 일정 내 챌린지 달성 자동화 로직 복잡도 → MVP는 실시간 트리거 방식으로 단순화
  - 발표 시점 실제 사용자 수 부족으로 랭킹 의미 없을 수 있음 → 시드 더미 데이터 20건 이상 사전 삽입
  - **(Ver1.2)** Gunicorn gthread/eventlet 워커 전환 시 DB 커넥션 풀 소진 대기/503 처리 미구현 — 후속 이슈로 분리(#71)

- **열린 질문:**
  - SNS 공유 카드 이미지 생성 방식: html2canvas(클라이언트 캡처) 로 결정 — Safari 렌더링 이슈 QA 필요
  - 배달비 환산 기준 데이터(치킨 가격 등): `config.py` 상수 파일 하드코딩으로 결정, 추후 DB 이관

---

## 11. DB(ERD) 설계

### 테이블 정의

**users** *(Ver1.2: provider, provider_id, role 컬럼 추가)*

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK AUTO_INCREMENT | 사용자 고유 ID |
| email | VARCHAR(255) UNIQUE | 소셜 로그인 이메일 |
| nickname | VARCHAR(100) | 표시 이름 |
| hourly_wage | INT | 기본 시급 (원), 기본값 10030 — 마이페이지에서 수정 가능 (Ver1.2) |
| provider | VARCHAR(20) | 소셜 로그인 제공자 — `google` \| `kakao` (Ver1.2) |
| provider_id | VARCHAR(255) | OAuth sub / 카카오 회원번호 (Ver1.2) |
| role | VARCHAR(20) | 권한 — `user`(기본값) \| `admin`. 관리자 페이지 접근 제어 기준 (Ver1.2 신규, 예정) |
| created_at | DATETIME | 가입일 |

> `(provider, provider_id)` UNIQUE 제약 — `upsert_user_profile`이 재로그인 시 닉네임을 갱신하며 기존 id를 반환 (Ver1.2)
> `role`은 Cloudtype DB 콘솔에서 직접 `UPDATE users SET role='admin' WHERE id=...`로 지정한다 (Ver1.2, 별도 관리 UI 없음)

**delivery_records**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | CHAR(36) PK (UUID) | |
| user_id | BIGINT FK → users.id | 데이터 접근 필터 기준 컬럼 |
| total_price | INT | 총 주문 금액 (원) |
| delivery_fee | INT | 배달비 (원) |
| total_calories | INT | 총 칼로리 (kcal) |
| items | JSON | 음식 항목 배열 `[{name, price, calories}]` |
| ai_comment | TEXT | LLM 공감 코멘트 |
| created_at | DATETIME | 분석 일시 |

**time_records**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | CHAR(36) PK (UUID) | |
| user_id | BIGINT FK → users.id | 데이터 접근 필터 기준 컬럼 |
| youtube_min | INT | 유튜브 사용 시간 (분) |
| instagram_min | INT | 인스타 사용 시간 (분) |
| tiktok_min | INT | 틱톡 사용 시간 (분) |
| game_min | INT | 게임 사용 시간 (분) |
| hourly_wage | INT | 적용 시급 (원) |
| ai_comment | TEXT | LLM 공감 코멘트 |
| created_at | DATETIME | 분석 일시 |

**dopamine_scores**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | CHAR(36) PK (UUID) | |
| user_id | BIGINT FK → users.id | 데이터 접근 필터 기준 컬럼 |
| score | INT (0~100) | 도파민 점수 |
| delivery_contribution | INT (0~40) | 배달 기여 점수 |
| time_contribution | INT (0~40) | 시간 기여 점수 |
| challenge_bonus | INT (0~20) | 챌린지 보너스 점수 |
| week_start | DATE | 해당 주 시작일 (월요일) |
| created_at | DATETIME | 산출 일시 |

> `(user_id, week_start)` UNIQUE 제약 — 주차별 1개 레코드 upsert (`services/score_service.recalculate_score`)

**challenges**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | CHAR(36) PK (UUID) | |
| title | VARCHAR(255) | 챌린지 제목 |
| description | TEXT | 상세 설명 |
| target_type | VARCHAR(20) | `delivery` / `time` / `both` |
| target_value | INT | 목표 수치 |
| is_ai_generated | TINYINT(1) | AI 추천 여부, 기본값 0 |

**user_challenges**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | CHAR(36) PK (UUID) | |
| user_id | BIGINT FK → users.id | 데이터 접근 필터 기준 컬럼 |
| challenge_id | CHAR(36) FK → challenges | |
| progress | INT | 현재 달성값 |
| is_completed | TINYINT(1) | 달성 여부, 기본값 0 |
| started_at | DATETIME | 참여 시작일 |
| completed_at | DATETIME (nullable) | 달성일 — 홈 챌린지 집계 기준 컬럼 (Ver1.2) |

> `(user_id, challenge_id, is_completed=false)` — 활성 중복 참여 불가 처리 (앱 레벨, FR-35)

### 데이터 접근 정책

```sql
-- RLS는 사용하지 않는다 (Ver1.2: #21 전환에서 제거됨).
-- 모든 조회/수정은 앱에서 WHERE user_id = session['user_id'] 로 스코프한다.
-- 예시: delivery_records
SELECT * FROM delivery_records WHERE user_id = %s AND ...
```

모든 테이블(delivery_records, time_records, dopamine_scores, user_challenges)에 동일 패턴 적용.

---

## 12. 백엔드 아키텍처 설계

### 프로젝트 디렉토리 구조 *(Ver1.2: 실제 구현 기준 갱신)*

```
dopacheck/
├── app.py                   Flask 앱 진입점 (Blueprint 등록, 세션 쿠키 보안, 413 핸들러)
├── config.py                환산 기준 상수
├── requirements.txt         flask, pymysql, DBUtils, authlib, anthropic 등
│
├── ai/                      AI 모듈 패키지 (오영석 담당)
│   ├── __init__.py
│   ├── ocr.py               영수증 OCR 파싱
│   ├── calorie.py           칼로리 추론
│   ├── comment.py           공감 코멘트 생성
│   ├── score.py             도파민 점수 산출 로직
│   ├── challenge.py         챌린지 추천
│   └── utils.py             (Ver1.2) extract_text 등 공통 헬퍼 + 모델 상수 중앙화
│
├── services/                (Ver1.2 신규) 도메인 공통 서비스
│   └── score_service.py     recalculate_score — 점수 재산출/upsert 공통 함수
│
├── utils/                   (Ver1.2 신규) 공통 유틸
│   ├── week.py              KST 기준 주차 범위 계산 (get_week_ranges)
│   └── csrf.py              CSRF 토큰 발급/검증 공통화
│
├── routes/                  Flask 라우트 (각 담당자)
│   ├── auth.py               소셜 로그인/로그아웃
│   ├── delivery.py           /delivery — 김관영
│   ├── time.py               /time — 이은석
│   ├── report.py             /report — 정재봉
│   ├── history.py            /history — 허남
│   ├── score.py               /score — 김승현
│   ├── challenge.py           /challenge — 오영석
│   ├── mypage.py              (Ver1.2 신규) /mypage — 마이페이지·시급 설정 — 김승현
│   ├── admin.py                (Ver1.2 신규, 예정) /admin — 통계 대시보드, admin_required 가드 — 김승현
│   ├── home.py                홈 대시보드
│   └── dev_only.py            개발 환경(FLASK_ENV=development) 전용 더미 로그인
│
├── db/                      MariaDB 연동 (김승현)
│   ├── client.py             커넥션 풀(DBUtils.PooledDB) 기반 db() 컨텍스트매니저, upsert_user_profile
│   └── schema.sql            테이블 정의
│
└── templates/               Jinja2 템플릿 (각 담당자)
    ├── base.html / _app_base.html
    ├── components/           header.html(아바타 드롭다운), footer.html (Ver1.2 신규 공통 컴포넌트)
    ├── delivery/ time/ report/ history/ score/ challenge/
    ├── mypage/                (Ver1.2 신규) mypage.html
    └── admin/                 (Ver1.2 신규, 예정) index.html — 통계 대시보드
```

### API 라우트 구조 *(Ver1.2: /mypage 추가)*

```
Flask App (Cloudtype)
├── GET  /                    홈 리다이렉트
├── GET  /login               소셜 로그인 페이지
├── GET  /delivery            영수증 업로드 폼
├── POST /delivery/analyze    영수증 분석 → ai.ocr + ai.calorie + ai.comment 호출
├── GET  /time                시간 입력 폼
├── POST /time/analyze        시간 분석 → ai.comment 호출 (CSRF 검증)
├── GET  /report               종합 리포트 → ai.comment 호출 + recalculate_score 재산출
├── GET  /history               히스토리 목록
├── GET  /history/<id>          히스토리 상세
├── DELETE /history/<id>        히스토리 삭제 (CSRF 검증)
├── GET  /score                 도파민 점수 (시간 통계 = SUM, game_min 포함)
├── GET  /challenge              챌린지 목록
├── POST /challenge/<id>/join    챌린지 참여 → ai.challenge 호출
├── GET  /mypage                 (Ver1.2 신규) 마이페이지 — 내 정보/점수/챌린지/분석 횟수
├── POST /mypage/update_wage     (Ver1.2 신규) 기본 시급 수정
└── GET  /admin                  (Ver1.2 신규, 예정) 관리자 통계 대시보드 — role='admin' 전용,
                                  비관리자 접근 시 / 로 리다이렉트
```

### AI 모듈 내부 함수 구조 (오영석 — Flask 내부 패키지)

#### POST /ocr
```json
// Request (multipart/form-data)
{ "image": <file> }

// Response
{
  "success": true,
  "items": [
    { "name": "후라이드치킨", "price": 18000, "quantity": 1 }
  ],
  "delivery_fee": 3000,
  "total_price": 21000
}
```

#### POST /calorie
```json
// Request
{ "items": ["후라이드치킨", "콜라"] }

// Response
{
  "success": true,
  "calories": [
    { "name": "후라이드치킨", "kcal": 1800 },
    { "name": "콜라", "kcal": 140 }
  ],
  "total_kcal": 1940
}
```

#### POST /comment
```json
// Request
{
  "type": "delivery",  // "delivery" | "time" | "report"
  "context": {
    "total_price": 21000,
    "total_kcal": 1940,
    "conversions": ["치킨 1.2마리값", "러닝 28분"]
  }
}

// Response
{
  "success": true,
  "comment": "오늘도 맛있는 걸 드셨군요! 그 칼로리, 러닝 28분이면 다 태울 수 있어요. 내일 한 번 해볼까요?"
}
```

#### POST /score
```json
// Request
{
  "delivery_total": 47000,
  "time_total_min": 870,
  "challenge_completed": 2
}

// Response
{
  "success": true,
  "score": 72,
  "delivery_contribution": 28,
  "time_contribution": 30,
  "challenge_bonus": 14
}
```

> **(Ver1.2)** 위 산출 로직은 `services/score_service.recalculate_score(user_id)`에서 이번 주(KST, 월요일 시작) 배달/시간/챌린지 데이터를 집계해 `dopamine_scores`에 upsert하는 형태로 통합 호출된다. 시간 데이터는 `youtube_min + instagram_min + tiktok_min + game_min`의 주간 합계를 사용한다.

#### POST /challenge
```json
// Request
{
  "history": {
    "avg_delivery_per_week": 3.2,
    "top_app": "youtube",
    "top_app_hours": 6.5
  }
}

// Response
{
  "success": true,
  "recommendations": [
    {
      "title": "이번 주 배달 2회 이하",
      "description": "평소보다 1.2회 줄여보세요!",
      "target_type": "delivery",
      "target_value": 2
    }
  ]
}
```

---

## 13. 시스템 아키텍처 설계

```
[사용자 브라우저]
       │
       ▼
[Flask + Jinja2 — Cloudtype]
       │
       ├─── 인증: Flask 세션 (Google / Kakao OAuth)
       │           └── 세션 쿠키 기반 로그인 상태 유지
       │               (HTTPONLY, SAMESITE=Lax, SECURE는 SESSION_COOKIE_SECURE/FLASK_ENV로 분리 — Ver1.2)
       │
       ├─── DB: MariaDB (Cloudtype)
       │         ├── DBUtils.PooledDB 커넥션 풀 (DB_POOL_SIZE / DB_POOL_TIMEOUT→503) — Ver1.2~1.3
       │         └── user_id 필터로 사용자별 데이터 격리
       │
       ├─── 프론트: Tailwind CSS (Play CDN → PostCSS 빌드 전환 — Ver1.2)
       │
       └─── AI 모듈 (Flask 내부 패키지 ai/) + services/score_service.py
                         ├── POST /ocr
                         ├── POST /calorie
                         ├── POST /comment
                         ├── POST /score (recalculate_score로 오케스트레이션)
                         └── POST /challenge
                                  │
                                  └── Claude API (claude-haiku-4-5 — config.py)
```

### 배포 구성

| 역할 | 플랫폼 | 담당 |
|------|--------|------|
| Flask 앱 서버 | Cloudtype | 김관영 |
| 앱 배포 | Cloudtype | 이은석 |
| DB | MariaDB (Cloudtype) | 김승현 |
| AI 모듈 | Flask 내장 (ai/ 패키지) | 오영석 |

### 환경변수 목록 *(Ver1.2: DB_POOL_SIZE, SESSION_COOKIE_SECURE 추가 / Ver1.3: DB_POOL_TIMEOUT 추가)*

| 변수명 | 설명 | 관리자 |
|--------|------|--------|
| `DB_HOST` | MariaDB 호스트 (Cloudtype 제공) | 김승현 |
| `DB_PORT` | MariaDB 포트 (기본 3306) | 김승현 |
| `DB_NAME` | 데이터베이스명 | 김승현 |
| `DB_USER` | DB 사용자명 | 김승현 |
| `DB_PASSWORD` | DB 비밀번호 | 김승현 |
| `DB_POOL_SIZE` | (Ver1.2) DB 커넥션 풀 최대 크기, 미설정 시 5 | 김승현 |
| `DB_POOL_TIMEOUT` | (Ver1.3) 풀 소진 시 커넥션 대기 한도(초), 미설정 시 30 — 초과 시 503 반환(#71) | 정재봉 |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID | 김승현 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 시크릿 | 김승현 |
| `KAKAO_CLIENT_ID` | Kakao OAuth 클라이언트 ID (scope: profile_image 포함, Ver1.2) | 김승현 |
| `ANTHROPIC_API_KEY` | Claude API 키 | 오영석 |
| `FLASK_SECRET_KEY` | Flask 세션 암호화 키 | 김관영 |
| `FLASK_ENV` | `development` \| `production` — ProxyFix·세션 쿠키 SECURE·dev_only 라우트 게이팅 | 김관영 |
| `SESSION_COOKIE_SECURE` | (Ver1.2) `true`/`false` — 세션 쿠키 SECURE 속성 명시 분리(미설정 시 FLASK_ENV=production 기준) | 김관영 |

---

## 14. 구현 시작 최소 조건 체크리스트 *(Ver1.2 기준 진행 현황)*

- [x] 도파민 점수 공식 팀 합의 완료 (배달 40% + 시간 40% + 챌린지 20%)
- [x] AI 모듈 API 엔드포인트 스펙 문서 공유 완료 (오영석)
- [x] Cloudtype MariaDB 서버 생성 및 DB 스키마 적용 완료 (김승현)
- [x] Flask 서버 Cloudtype 배포 및 환경변수 설정 완료 (이은석)
- [x] Google / Kakao OAuth 키 발급 완료 (김승현 + 김관영)
- [x] GitHub 레포지토리 생성 및 브랜치 전략 공유 완료 (정재봉)
- [x] 환산 기준 상수값 config.py 파일 공유 완료
- [ ] 시드 더미 데이터 20건 MariaDB 삽입 완료 (랭킹 기능 시연용) — `db/seed.sql` 작성 필요 (김승현)
