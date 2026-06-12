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

    공식: 배달 기여(40%) + 시간 기여(40%) + 챌린지 보너스(20%) — config.py 가중치 사용

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
            "delivery_contribution": 28,   # 0~40
            "time_contribution": 30,       # 0~40
            "challenge_bonus": 14          # 0~20
        }
    """
    delivery_total = int(data.get("delivery_total", 0))
    time_total_min = int(data.get("time_total_min", 0))
    challenge_completed = int(data.get("challenge_completed", 0))

    max_delivery_score = int(SCORE_DELIVERY_WEIGHT * 100)    # 40
    max_time_score = int(SCORE_TIME_WEIGHT * 100)            # 40
    max_challenge_bonus = int(SCORE_CHALLENGE_WEIGHT * 100)  # 20

    delivery_contribution = max(
        0,
        round((1 - min(delivery_total, _DELIVERY_MAX) / _DELIVERY_MAX) * max_delivery_score),
    )
    time_contribution = max(
        0,
        round((1 - min(time_total_min, _TIME_MAX) / _TIME_MAX) * max_time_score),
    )
    challenge_bonus = min(max_challenge_bonus, challenge_completed * CHALLENGE_COMPLETE_BONUS)

    score = delivery_contribution + time_contribution + challenge_bonus

    return {
        "success": True,
        "score": score,
        "delivery_contribution": delivery_contribution,
        "time_contribution": time_contribution,
        "challenge_bonus": challenge_bonus,
    }
