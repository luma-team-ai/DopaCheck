# PRD — 도파민 대리 만족 (Dopamine Check)

> AI 심화 과정 팀 프로젝트 | 6인 팀 | 개발 기간: 6~7일  
> 작성일: 2026-06-11  
> 팀원: 김승현, 김관영, 이은석, 정재봉, 허남, 오영석

---

## 1. 배경

- **현재 문제:**  
  사람들은 배달 앱 주문, SNS, 유튜브, 게임 등 즉각적인 도파민 자극 소비에 익숙해져 있으나, 자신이 얼마나 많은 돈과 시간을 소비하는지 체감하지 못한다. 소비 행위 자체가 무의식적으로 이루어지기 때문에 반성이나 변화의 계기를 갖기 어렵다.

- **왜 지금 필요한가:**  
  배달 앱 사용량 및 스마트폰 평균 사용 시간이 꾸준히 증가하고 있으며, MZ세대를 중심으로 소비 패턴에 대한 자기 인식 요구가 높아지고 있다. 데이터 시각화와 AI 기반 인사이트를 통해 "대리 만족"이라는 심리적 각성 효과를 제공하는 서비스가 필요하다.

- **관련 문서/이슈:**
  - 기술 스택: Flask, Jinja2, Supabase(PostgreSQL), Cloudtype
  - AI 모듈: OCR(영수증 파싱), LLM(칼로리 추론·공감 코멘트·챌린지 추천·점수 산출)
  - 오영석 담당 AI 서비스 모듈 — Flask 앱 내부 모듈로 통합 (ai/ 패키지)

---

## 2. 목표

- **사용자가 무엇을 할 수 있어야 하는가:**
  1. 배달 영수증을 업로드하면 지출 금액·칼로리를 자동 분석하고, "치킨 N마리값", "러닝 N분" 등으로 환산된 결과를 확인할 수 있다.
  2. SNS·유튜브·게임 사용 시간을 입력하면 "책 N권", "시급 N원짜리 취미" 등으로 환산된 시간 소비 리포트를 확인할 수 있다.
  3. 종합 도파민 점수와 히스토리를 통해 자신의 소비 패턴 변화를 추적할 수 있다.
  4. AI가 추천한 챌린지에 참여해 소비 습관 개선 목표를 설정하고 달성률을 확인할 수 있다.

- **비즈니스 또는 운영상 기대 효과:**
  - AI 심화 과정 발표에서 OCR·LLM·데이터 시각화를 실제 서비스에 통합한 사례로 시연
  - 사용자에게 소비 패턴에 대한 자기 인식(각성)과 공감을 동시에 제공

---

## 3. 대상 사용자

- **주요 사용자:** 배달 앱과 SNS를 자주 이용하는 20~30대. 자신의 소비 패턴을 돌아보고 싶지만 번거로운 기록은 하고 싶지 않은 사람.
- **보조 사용자:** AI 심화 과정 강사 및 수강생 (발표 청중)
- **관리자 또는 운영자 영향:** Supabase 대시보드를 통한 사용자 데이터 조회. 별도 관리자 페이지는 MVP 범위 외.

---

## 4. 범위

이번 작업에 포함:

- [x] 소셜 로그인 (Google / Kakao) — 모든 기능 로그인 필수, 비로그인 접근 불가
- [x] 배달 영수증 OCR 파싱 및 분석 (`/delivery`) — 김관영
- [x] 시간 소비 입력 및 환산 분석 (`/time`) — 이은석
- [x] 종합 리포트 + SNS 공유 카드 (`/report`) — 정재봉
- [x] 분석 히스토리 조회 및 삭제 (`/history`) — 허남
- [x] 도파민 점수 산출 및 랭킹 (`/score`) — 김승현
- [x] AI 챌린지 추천 및 참여 (`/challenge`) — 오영석
- [x] AI 서비스 모듈 (OCR, LLM 칼로리 추론, 공감 코멘트, 점수 산출) — 오영석, Flask 내부 모듈 (ai/ 패키지)

이번 작업에 포함하지 않음:

- [ ] 별도 관리자 페이지
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
5. 결과가 Supabase에 저장되고 히스토리·도파민 점수에 즉시 반영된다.

### 흐름 B — 시간 시각화
1. 사용자가 로그인 후 `/time` 에 접속해 앱별 주간 사용 시간(시간 단위)과 시급을 입력한다.
2. AI 모듈이 시간 환산("책 N권", "시급 N원짜리 취미")과 LLM 공감 코멘트를 반환한다.
3. 시스템이 도넛 차트와 환산 결과를 화면에 표시한다.
4. 결과가 Supabase에 저장되고 히스토리·도파민 점수에 즉시 반영된다.

### 흐름 C — 챌린지
1. 사용자가 로그인 후 `/challenge` 에 접속하면 AI가 히스토리 기반 맞춤 챌린지를 추천한다.
2. 사용자가 챌린지를 선택하고 목표를 설정한다.
3. 이후 배달/시간 분석 결과가 쌓이면 달성률이 자동 업데이트된다.
4. 챌린지 달성 시 도파민 점수에 보너스(+5점)가 반영된다.

### 흐름 D — 비로그인 접근
1. 비로그인 사용자가 임의의 URL에 접근한다.
2. 시스템이 `/login` 으로 즉시 리다이렉트한다.

---

## 6. 기능 요구사항

### 공통 인증 (김승현)
- FR-0: 모든 페이지는 로그인 상태를 확인하며, 비로그인 사용자는 `/login`으로 리다이렉트한다.
- FR-0-1: 사용자는 Google 또는 Kakao 소셜 로그인으로 가입/로그인할 수 있어야 한다.

### 배달 분석 (`/delivery` — 김관영)
- FR-1: 사용자는 JPG·PNG 형식의 영수증 이미지를 업로드할 수 있어야 한다.
- FR-2: OCR AI 모듈은 음식명·단가·수량·배달비를 추출해야 한다.
- FR-3: LLM AI 모듈은 추출된 음식명을 기반으로 칼로리(kcal)를 추론해야 한다.
- FR-4: 시스템은 총 지출을 "치킨 N마리 / 헬스장 N개월" 단위로 환산해야 한다.
- FR-5: 시스템은 총 칼로리를 "러닝 N분 / 걷기 N시간" 단위로 환산해야 한다.
- FR-6: LLM은 분석 결과 기반 공감 코멘트를 생성해야 한다.
- FR-7: OCR 파싱 실패 시 사용자에게 수동 입력 폼(fallback)을 제공해야 한다.
- FR-8: 분석 결과는 Supabase에 저장되고 히스토리·점수에 즉시 반영되어야 한다.

### 시간 시각화 (`/time` — 이은석)
- FR-9: 사용자는 유튜브·인스타·틱톡·게임별 주간 사용 시간을 시간(h) 단위로 입력할 수 있어야 한다.
- FR-10: 사용자는 시급(원)을 입력할 수 있어야 한다.
- FR-11: 시스템은 SNS 시간을 "책 N권 / 강의 N개 / 운동 N회"로 환산해야 한다.
- FR-12: 시스템은 게임 시간을 "시급 기준 N원짜리 취미"로 환산해야 한다.
- FR-13: 시스템은 앱별 사용 시간 비율 도넛 차트를 렌더링해야 한다.
- FR-14: LLM은 분석 결과 기반 공감 코멘트를 생성해야 한다.
- FR-15: 분석 결과는 Supabase에 저장되고 히스토리·점수에 즉시 반영되어야 한다.

### 종합 리포트 (`/report` — 정재봉)
- FR-16: 시스템은 배달 지출·시간 소비 통합 대시보드를 표시해야 한다.
- FR-17: LLM은 종합 인사이트 코멘트를 생성해야 한다.
- FR-18: 시스템은 도파민 점수를 표시해야 한다.
- FR-19: 사용자는 결과 카드를 이미지로 저장하거나 SNS 공유할 수 있어야 한다. (html2canvas 활용)
- FR-20: 저번 주 vs 이번 주 비교 차트를 표시해야 한다. (추가 기능)

### 히스토리 (`/history` — 허남)
- FR-21: 사용자는 날짜별 분석 기록 목록을 조회할 수 있어야 한다.
- FR-22: 사용자는 특정 기록의 상세 내용을 조회할 수 있어야 한다.
- FR-23: 사용자는 기록을 삭제할 수 있어야 한다.
- FR-24: 사용자는 이번 주 / 이번 달 / 전체 기간 필터를 적용할 수 있어야 한다.
- FR-25: 같은 날 동일 유형 분석을 여러 번 하면 누적 저장된다. (덮어쓰기 없음)

### 도파민 점수 (`/score` — 김승현)
- FR-26: AI 모듈은 배달·시간 데이터를 기반으로 도파민 점수(0~100)를 산출해야 한다.
- FR-27: 점수 산출 공식: `배달 기여(40%) + 시간 기여(40%) + 챌린지 보너스(20%)`
- FR-28: 시스템은 점수 구성 항목별 기여도를 시각화해야 한다.
- FR-29: 시스템은 전체 사용자 평균 대비 내 점수를 표시해야 한다.
- FR-30: 시스템은 상위 N% 랭킹을 표시해야 한다. (시드 더미 데이터 20건 이상 사전 삽입)
- FR-31: 새 분석 결과 저장 시 도파민 점수를 즉시 재산출(upsert)해야 한다.

### 챌린지 (`/challenge` — 오영석)
- FR-32: 시스템은 기본 챌린지 목록을 제공해야 한다. (예: "이번 주 배달 3회 이하", "SNS 하루 1시간 이하")
- FR-33: AI 모듈은 사용자 히스토리 기반 맞춤 챌린지를 추천해야 한다.
- FR-34: 사용자는 챌린지를 선택하고 목표를 설정할 수 있어야 한다.
- FR-35: 동일 챌린지는 활성 상태에서 중복 참여 불가하다.
- FR-36: 시스템은 챌린지 달성률 프로그레스 바를 표시해야 한다.
- FR-37: 챌린지 달성 판정은 분석 결과 저장 시 실시간 트리거 방식으로 처리한다.
- FR-38: 챌린지 달성 시 도파민 점수에 +5점 보너스가 반영되어야 한다.

### AI 서비스 모듈 (오영석 — 별도 API 서버)
- FR-39: AI 모듈은 Flask 앱 내부 패키지(ai/)로 통합되며, 각 라우트에서 직접 함수 호출 방식으로 사용한다.
- FR-40: `ai.ocr.parse_receipt(image_bytes)` — 이미지 바이트를 입력받아 구조화된 dict 반환
- FR-41: `ai.calorie.estimate(items)` — 음식명 배열을 입력받아 kcal dict 반환
- FR-42: `ai.comment.generate(type, context)` — 분석 컨텍스트를 입력받아 공감 코멘트 문자열 반환
- FR-43: `ai.score.calculate(data)` — 배달·시간 데이터를 입력받아 점수 dict 반환
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
  - Supabase RLS(Row Level Security) 적용 — 본인 데이터만 조회 가능
  - AI 모듈 API 키는 환경변수(.env)로 관리, 코드에 하드코딩 금지

- **로깅/모니터링:**
  - AI 모듈 API 호출 실패 시 에러 로그 기록
  - Cloudtype 서버 에러 로그 수집

---

## 8. 수용 기준

### 인증
- [x] Given 비로그인 사용자가, When 어떤 페이지에 접근하더라도, Then 로그인 페이지(`/login`)로 리다이렉트된다.
- [ ] Given 사용자가, When Google/Kakao 소셜 로그인을 완료하면, Then 홈 화면으로 이동한다.

### 배달 분석
- [ ] Given 로그인한 사용자가, When 영수증 이미지를 업로드하면, Then OCR이 음식명과 금액을 추출하여 화면에 표시한다.
- [ ] Given OCR 추출 결과가 있을 때, When 사용자가 수정 후 확인하면, Then 수정된 값 기준으로 칼로리·환산 결과가 계산된다.
- [ ] Given OCR 파싱에 실패하면, Then 수동 입력 폼이 표시된다.
- [ ] Given 분석이 완료되면, When 결과 화면이 표시될 때, Then LLM 공감 코멘트가 함께 출력된다.
- [ ] Given 분석이 완료되면, Then 결과가 Supabase에 저장되고 히스토리에서 조회된다.

### 시간 시각화
- [ ] Given 로그인한 사용자가, When 앱별 시간(h)과 시급을 입력하면, Then 환산 결과와 도넛 차트가 표시된다.
- [ ] Given 시간 분석이 완료되면, Then 결과가 Supabase에 저장되고 히스토리에서 조회된다.

### 도파민 점수
- [ ] Given 배달 또는 시간 분석이 저장되면, Then 도파민 점수가 즉시 재산출되어 `/score`에 반영된다.
- [ ] Given 사용자가 `/score`에 접속하면, Then 점수·항목별 기여도·상위 N% 랭킹이 표시된다.

### 챌린지
- [ ] Given 히스토리 데이터가 1건 이상 있을 때, When 챌린지 페이지에 접속하면, Then AI 맞춤 추천 챌린지가 표시된다.
- [ ] Given 동일 챌린지가 이미 활성 상태일 때, When 다시 참여를 시도하면, Then 중복 참여가 차단된다.
- [ ] Given 챌린지를 달성하면, Then 도파민 점수에 +5점 보너스가 반영된다.

### AI 모듈
- [ ] Given AI 모듈 API 호출이 실패하면, Then 사용자에게 에러 메시지가 표시되고 수동 입력 fallback이 제공된다.
- [ ] Given 타 도메인에서 AI 모듈 API를 호출하면, Then CORS 오류 없이 정상 응답한다.

---

## 9. 검증 계획

- **단위 테스트:**
  - AI 모듈: 샘플 영수증 5종(배달의민족·쿠팡이츠) OCR 파싱 정확도 — 음식명·금액 추출 성공률 80% 이상 목표
  - 환산 로직: 칼로리→운동, 지출→대체재, 시간→대체활동 함수 경계값(0, 음수, 매우 큰 값) 테스트
  - 도파민 점수 산출 함수 입력/출력 검증

- **통합 테스트:**
  - 영수증 업로드 → OCR → LLM 칼로리 추론 → DB 저장 → 히스토리 조회 → 점수 반영 전체 흐름 (Day 5)
  - 시간 입력 → 환산 → DB 저장 → 히스토리 조회 → 점수 반영 전체 흐름 (Day 5)
  - 챌린지 참여 → 분석 저장 → 달성 판정 → 점수 보너스 반영 흐름 (Day 5)

- **수동 확인:**
  - 발표 시연용 데모 시나리오 전체 흐름 1회 완주 (Day 6)
  - 모바일 브라우저(Chrome, Safari) UI 확인
  - 로그인/로그아웃 및 RLS 권한 격리 확인
  - 시드 더미 데이터 기반 랭킹 정상 표시 확인

---

## 10. 리스크와 열린 질문

- **리스크:**
  - OCR 정확도: 배달 영수증 레이아웃이 앱마다 달라 파싱 실패 가능 → 수동 수정 fallback 필수
  - LLM 응답 지연: 공감 코멘트 생성이 5초 이상 걸릴 경우 UX 저하 → 로딩 스피너 + 타임아웃 처리 필요
  - Supabase RLS 미적용 시 타 사용자 데이터 노출 위험 → Day 1 선제 처리
  - AI 모듈이 Flask 내부 모듈로 통합되어 CORS 이슈 없음 (동일 서비스)
  - 6~7일 일정 내 챌린지 달성 자동화 로직 복잡도 → MVP는 실시간 트리거 방식으로 단순화
  - 발표 시점 실제 사용자 수 부족으로 랭킹 의미 없을 수 있음 → 시드 더미 데이터 20건 이상 사전 삽입

- **열린 질문:**
  - SNS 공유 카드 이미지 생성 방식: html2canvas(클라이언트 캡처) 로 결정 — Safari 렌더링 이슈 QA 필요
  - 배달비 환산 기준 데이터(치킨 가격 등): `config.py` 상수 파일 하드코딩으로 결정, 추후 DB 이관

---

## 11. DB(ERD) 설계

### 테이블 정의

**users**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | Supabase Auth 연동 |
| email | text | 소셜 로그인 이메일 |
| nickname | text | 표시 이름 |
| hourly_wage | integer | 기본 시급 (원), 기본값 10030 |
| created_at | timestamptz | 가입일 |

**delivery_records**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| user_id | uuid FK → users | RLS 기준 컬럼 |
| total_price | integer | 총 주문 금액 (원) |
| delivery_fee | integer | 배달비 (원) |
| total_calories | integer | 총 칼로리 (kcal) |
| items | jsonb | 음식 항목 배열 `[{name, price, calories}]` |
| ai_comment | text | LLM 공감 코멘트 |
| created_at | timestamptz | 분석 일시 |

**time_records**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| user_id | uuid FK → users | RLS 기준 컬럼 |
| youtube_min | integer | 유튜브 사용 시간 (분) |
| instagram_min | integer | 인스타 사용 시간 (분) |
| tiktok_min | integer | 틱톡 사용 시간 (분) |
| game_min | integer | 게임 사용 시간 (분) |
| hourly_wage | integer | 적용 시급 (원) |
| ai_comment | text | LLM 공감 코멘트 |
| created_at | timestamptz | 분석 일시 |

**dopamine_scores**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| user_id | uuid FK → users | RLS 기준 컬럼 |
| score | integer | 도파민 점수 (0~100) |
| delivery_contribution | integer | 배달 기여 점수 (0~40) |
| time_contribution | integer | 시간 기여 점수 (0~40) |
| challenge_bonus | integer | 챌린지 보너스 점수 (0~20) |
| week_start | date | 해당 주 시작일 (월요일) |
| created_at | timestamptz | 산출 일시 |

> `(user_id, week_start)` UNIQUE 제약 — 주차별 1개 레코드 upsert

**challenges**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| title | text | 챌린지 제목 |
| description | text | 상세 설명 |
| target_type | text | `delivery` / `time` / `both` |
| target_value | integer | 목표 수치 |
| is_ai_generated | boolean | AI 추천 여부, 기본값 false |

**user_challenges**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| user_id | uuid FK → users | RLS 기준 컬럼 |
| challenge_id | uuid FK → challenges | |
| progress | integer | 현재 달성값 |
| is_completed | boolean | 달성 여부, 기본값 false |
| started_at | timestamptz | 참여 시작일 |
| completed_at | timestamptz | 달성일 (nullable) |

> `(user_id, challenge_id, is_completed=false)` — 활성 중복 참여 불가 처리

### RLS 정책 (Supabase)

```sql
-- 예시: delivery_records
CREATE POLICY "본인 데이터만 조회"
ON delivery_records FOR ALL
USING (auth.uid() = user_id);
```

모든 테이블(delivery_records, time_records, dopamine_scores, user_challenges)에 동일 패턴 적용.

---

## 12. 백엔드 아키텍처 설계

### 프로젝트 디렉토리 구조

```
dopamine-check/
├── app.py                   Flask 앱 진입점
├── config.py                환산 기준 상수
├── requirements.txt
│
├── ai/                      AI 모듈 패키지 (오영석 담당)
│   ├── __init__.py
│   ├── ocr.py               영수증 OCR 파싱
│   ├── calorie.py           칼로리 추론
│   ├── comment.py           공감 코멘트 생성
│   ├── score.py             도파민 점수 산출
│   └── challenge.py         챌린지 추천
│
├── routes/                  Flask 라우트 (각 담당자)
│   ├── delivery.py          /delivery — 김관영
│   ├── time.py              /time — 이은석
│   ├── report.py            /report — 정재봉
│   ├── history.py           /history — 허남
│   ├── score.py             /score — 김승현
│   └── challenge.py         /challenge — 오영석
│
├── db/                      Supabase 연동 (김승현)
│   └── client.py
│
└── templates/               Jinja2 템플릿 (각 담당자)
    ├── base.html
    ├── delivery/
    ├── time/
    ├── report/
    ├── history/
    ├── score/
    └── challenge/
```

### API 라우트 구조

```
Flask App (Cloudtype)
├── GET  /                    홈 리다이렉트
├── GET  /login               소셜 로그인 페이지
├── GET  /delivery            영수증 업로드 폼
├── POST /delivery/analyze    영수증 분석 → ai.ocr + ai.calorie + ai.comment 호출
├── GET  /time                시간 입력 폼
├── POST /time/analyze        시간 분석 → ai.comment 호출
├── GET  /report              종합 리포트 → ai.comment 호출
├── GET  /history             히스토리 목록
├── GET  /history/<id>        히스토리 상세
├── DELETE /history/<id>      히스토리 삭제
├── GET  /score               도파민 점수 → ai.score 호출
└── GET  /challenge           챌린지 목록
    POST /challenge/<id>/join 챌린지 참여 → ai.challenge 호출
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
       │
       ▼
[Flask + Jinja2 — Cloudtype]
       │
       ├─── 인증: Supabase Auth (Google / Kakao OAuth)
       │           └── 세션 쿠키 기반 로그인 상태 유지
       │
       ├─── DB: Supabase PostgreSQL
       │         └── RLS 적용 — 사용자별 데이터 격리
       │
       └─── AI 모듈 (Flask 내부 패키지 ai/)
                         ├── POST /ocr
                         ├── POST /calorie
                         ├── POST /comment
                         ├── POST /score
                         └── POST /challenge
                                  │
                                  └── Claude API (claude-sonnet-4-20250514)
```

### 배포 구성

| 역할 | 플랫폼 | 담당 |
|------|--------|------|
| Flask 앱 서버 | Cloudtype | 김관영 |
| 앱 배포 | Cloudtype | 이은석 |
| DB + 인증 | Supabase | 김승현 |
| AI 모듈 | Flask 내장 (ai/ 패키지) | 오영석 |

### 환경변수 목록

| 변수명 | 설명 | 관리자 |
|--------|------|--------|
| `SUPABASE_URL` | Supabase 프로젝트 URL | 김승현 |
| `SUPABASE_KEY` | Supabase anon key | 김승현 |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | 김승현 |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID | 김승현 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 시크릿 | 김승현 |
| `KAKAO_CLIENT_ID` | Kakao OAuth 클라이언트 ID | 김승현 |
| `ANTHROPIC_API_KEY` | Claude API 키 | 오영석 |

| `FLASK_SECRET_KEY` | Flask 세션 암호화 키 | 김관영 |

---

## 14. 구현 시작 최소 조건 체크리스트

- [ ] 도파민 점수 공식 팀 합의 완료 (배달 40% + 시간 40% + 챌린지 20%)
- [ ] AI 모듈 API 엔드포인트 스펙 문서 공유 완료 (오영석)
- [ ] Supabase 프로젝트 생성 및 DB 스키마 적용 완료 (김승현)
- [ ] RLS 정책 설정 완료 (김승현)
- [ ] Google / Kakao OAuth 키 발급 완료 (김승현)
- [ ] GitHub 레포지토리 생성 및 브랜치 전략 공유 완료 (정재봉)
- [ ] 환산 기준 상수값 config.py 파일 공유 완료
- [ ] 시드 더미 데이터 20건 Supabase 삽입 완료 (랭킹 기능 시연용)
