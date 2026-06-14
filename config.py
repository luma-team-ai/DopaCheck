"""환산 기준 상수 (PRD §10 — config.py 하드코딩으로 결정, 추후 DB 이관).

값은 팀 합의로 확정됨 (PRD §14 체크리스트 완료). 변경 시 팀 합의 후 반영할 것.
"""

# ── 지출 환산 기준 (FR-4) ────────────────────────────────
CHICKEN_PRICE = 20_000          # 치킨 1마리 (원)
GYM_MONTHLY_PRICE = 50_000      # 헬스장 1개월 (원)

# ── 칼로리 환산 기준 (FR-5) ──────────────────────────────
RUNNING_KCAL_PER_MIN = 10       # 러닝 1분당 소모 kcal
WALKING_KCAL_PER_HOUR = 250     # 걷기 1시간당 소모 kcal

# ── 시간 환산 기준 (FR-11, FR-12) ────────────────────────
BOOK_HOURS = 5                  # 책 1권 읽는 시간 (h)
LECTURE_HOURS = 2               # 강의 1개 수강 시간 (h)
WORKOUT_HOURS = 1               # 운동 1회 시간 (h)

# ── 기본값 ──────────────────────────────────────────────
DEFAULT_HOURLY_WAGE = 10_030    # 2026 최저시급 (원) — users.hourly_wage 기본값

# ── AI 클라이언트 설정 ────────────────────────────────────
AI_REQUEST_TIMEOUT = 15         # Anthropic API 타임아웃 (초)
AI_RECOMMEND_CACHE_TTL = 3_600  # AI 추천 세션 캐시 TTL (초 — 1시간)

# ── 도파민 점수 공식 (FR-27) ─────────────────────────────
SCORE_DELIVERY_WEIGHT = 0.4     # 배달 기여 40%
SCORE_TIME_WEIGHT = 0.4         # 시간 기여 40%
SCORE_CHALLENGE_WEIGHT = 0.2    # 챌린지 보너스 20%
CHALLENGE_COMPLETE_BONUS = 5    # 챌린지 달성 보너스 (FR-38)
