# 🧠 도파민 체크 (Dopamine Check)

> 배달 한 번, 스크롤 한 시간 — 내 도파민 소비를 숫자로 마주하는 서비스

배달 영수증을 올리면 **"치킨 1.2마리값, 러닝 28분어치"** 로, SNS·게임 시간을 입력하면 **"책 2권, 시급 N원짜리 취미"** 로 환산해 보여줍니다. AI가 공감 코멘트와 맞춤 챌린지를 제안하고, **종합 도파민 점수**(높을수록 소비 과다)로 패턴 변화를 추적합니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🍗 **배달 분석** | 영수증 사진 업로드 → AI(OCR) 자동 추출 → 지출·칼로리를 일상 활동으로 환산 + 공감 코멘트 |
| ⏰ **시간 분석** | 앱별 사용 시간 입력 → 대체 활동(책·강의·운동)·시급 기준 기회비용 환산 + 이번 주 누적 추적 |
| 📊 **종합 리포트** | 배달·시간·점수 통합 대시보드 + 주간 비교 |
| 🔥 **도파민 점수** | 0~100 점수 산출, 전체 평균 대비 / 상위 N% 랭킹 |
| 🏆 **AI 챌린지** | 내 히스토리 기반 맞춤 챌린지 추천, 달성 시 점수 감점(=개선) |
| 👤 **소셜 로그인** | Google · Kakao OAuth |

---

## 🚀 동작 방식

1. **로그인** — Google 또는 Kakao 계정으로 시작
2. **기록** — 배달 영수증 사진을 올리거나, SNS·게임 사용 시간을 입력
3. **환산** — AI가 지출·칼로리·시간을 일상 활동과 금전 가치로 환산하고 공감 코멘트를 남김
4. **점수·챌린지** — 종합 도파민 점수가 갱신되고, 내 패턴에 맞는 절제 챌린지를 추천
5. **추적** — 히스토리·주간 리포트·랭킹으로 변화를 확인

---

## 🛠 기술 스택

| 영역 | 사용 기술 |
|------|----------|
| 백엔드 | Python 3.10 · Flask · Jinja2 · Gunicorn |
| 데이터 | MariaDB (커넥션 풀, 앱 레벨 `user_id` 격리) |
| AI | Claude API (OCR·칼로리 추론·공감 코멘트·점수·챌린지 추천) |
| 인증 | OAuth 2.0 (Google · Kakao) |
| 프론트 | Tailwind CSS (빌드 산출물 서빙) · Chart.js |
| 배포 | Cloudtype (`main` push 시 자동 배포) |

---

## ⚡ 로컬 실행

> Python **3.10 이상** 필요 (소셜로그인 `authlib>=1.7` 요구사항).

```bash
git clone https://github.com/luma-team-ai/dopacheck.git
cd dopacheck

python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 환경변수 채우기 (아래 표 참조)

flask --app app run --debug   # http://localhost:5000
```

### 환경변수

| 변수 | 설명 |
|------|------|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MariaDB 연결 |
| `DB_POOL_SIZE` / `DB_POOL_TIMEOUT` | 커넥션 풀 크기(기본 5) / 풀 소진 대기 한도 초(기본 30, 초과 시 503) — 선택 |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `KAKAO_CLIENT_ID` | OAuth 자격증명 |
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `FLASK_SECRET_KEY` | 세션 암호화 키 |
| `SESSION_COOKIE_SECURE` | 세션 쿠키 Secure 속성 — `true` 또는 `FLASK_ENV=production`이면 활성화. 로컬은 `false` |

> ⚠️ `.env`는 절대 커밋하지 마세요.

---

## 📂 문서

- 📋 **[진행 현황 보드 → docs/STATUS.md](docs/STATUS.md)** — 머지 이력·남은 작업·인프라
- 📑 **[제품 요구사항 → docs/PRD.md](docs/PRD.md)** — 기능 명세(FR)·시나리오·ERD
- 🛠 **[개발팀 가이드 → docs/DEV_GUIDE.md](docs/DEV_GUIDE.md)** — 구조·역할·협업 규칙·배포·DB 전환 이력

---

## 👥 팀

AI 심화 과정 6인 팀 프로젝트

김승현 · 김관영 · 이은석 · 정재봉 · 허남 · 오영석
