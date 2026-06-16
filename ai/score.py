"""도파민 점수 산출 (담당: 오영석 — FR-43)."""

from config import (
    CHALLENGE_COMPLETE_BONUS,
    SCORE_CHALLENGE_WEIGHT,
    SCORE_DELIVERY_WEIGHT,
    SCORE_TIME_WEIGHT,
)

_DELIVERY_MAX = 200_000   # 주간 배달 지출 상한 기준 (원)
_TIME_MAX = 2_100         # 주간 SNS·게임 시간 상한 기준 (분 — 35시간/주)


def calculate(data: dict) -> dict:
    """배달·시간 데이터를 입력받아 도파민 점수(0~100)를 산출한다. (FR-26, FR-27)

    공식: 배달 기여(40%) + 시간 기여(40%) + 챌린지 감점(최대 -20) — config.py 가중치 사용

    점수 의미: 높을수록 도파민 위험도가 높음(나쁨). 배달·SNS 소비가 많을수록 점수↑,
    챌린지(줄이기) 달성 시 감점으로 위험도를 낮춤.

    예시: 배달 20만원/시간 2100분 → 배달 40 + 시간 40 = 80점(위험).
          챌린지 4개 달성 시 challenge_bonus=-20 → 최종 60점.

    Args:
        data: {
            "delivery_total": 47000,      # 주간 배달 총 지출 (원)
            "time_total_min": 870,        # 주간 SNS·게임 총 사용 시간 (분)
            "challenge_completed": 2      # 달성한 챌린지 수
        }

    Returns:
        {
            "success": True,
            "score": 72,
            "delivery_contribution": 28,   # 0~40 (많을수록 높음)
            "time_contribution": 30,       # 0~40 (많을수록 높음)
            "challenge_bonus": -10         # 0~-20 (챌린지 달성 감점, 음수 저장)
        }
    """
    delivery_total = max(0, int(data.get("delivery_total", 0)))
    time_total_min = max(0, int(data.get("time_total_min", 0)))
    challenge_completed = max(0, int(data.get("challenge_completed", 0)))

    max_delivery_score = int(SCORE_DELIVERY_WEIGHT * 100)    # 40
    max_time_score = int(SCORE_TIME_WEIGHT * 100)            # 40
    max_challenge_bonus = int(SCORE_CHALLENGE_WEIGHT * 100)  # 20

    # 배달 기여: 많을수록 점수↑ (도파민 위험도↑)
    delivery_contribution = round(min(delivery_total, _DELIVERY_MAX) / _DELIVERY_MAX * max_delivery_score)

    # 시간 기여: 많을수록 점수↑ (도파민 위험도↑)
    time_contribution = round(min(time_total_min, _TIME_MAX) / _TIME_MAX * max_time_score)

    # 챌린지 감점: 달성할수록 위험도↓ (음수로 저장)
    challenge_penalty = min(max_challenge_bonus, challenge_completed * CHALLENGE_COMPLETE_BONUS)
    challenge_bonus = -challenge_penalty  # 0~-20

    score = max(0, min(100, delivery_contribution + time_contribution + challenge_bonus))

    return {
        "success": True,
        "score": score,
        "delivery_contribution": delivery_contribution,
        "time_contribution": time_contribution,
        "challenge_bonus": challenge_bonus,
    }
