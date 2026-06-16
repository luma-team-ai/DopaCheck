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

# ── AI 모델 상수 (변경 시 이곳만 수정) ───────────────────
MODEL_OCR       = "claude-sonnet-4-6"
MODEL_CALORIE   = "claude-haiku-4-5"
MODEL_COMMENT   = "claude-haiku-4-5"
MODEL_CHALLENGE = "claude-haiku-4-5"

# ── OCR 비전 입력 튜닝 (#188) — sonnet-4-6 native 해상도 기준 ──
OCR_MAX_EDGE = 1568            # long edge 상한 px (sonnet급; Opus 4.7+는 2576)
OCR_MAX_VISION_TOKENS = 1568   # 비전 타일(토큰) 상한 ⌈w/28⌉×⌈h/28⌉ — 세로 영수증은 이게 먼저 걸림 (Opus 4.7+는 4784). 출력 토큰(OCR_MAX_OUTPUT_TOKENS)과 구분
OCR_TEMPERATURE = 0            # 추출 결정성 (정확도)
OCR_MAX_OUTPUT_TOKENS = 2048   # 긴 영수증 JSON 잘림 방지

# ── 도파민 점수 공식 (FR-27) ─────────────────────────────
SCORE_DELIVERY_WEIGHT = 0.4     # 배달 기여 40%
SCORE_TIME_WEIGHT = 0.4         # 시간 기여 40%
SCORE_CHALLENGE_WEIGHT = 0.2    # 챌린지 보너스 20%
CHALLENGE_COMPLETE_BONUS = 5    # 챌린지 달성 시 감점 폭(점/개) (FR-38)
