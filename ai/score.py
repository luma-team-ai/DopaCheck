"""도파민 점수 산출 (담당: 오영석 — FR-43)."""


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
    # TODO(오영석): 점수 산출 로직 구현 (LLM 또는 규칙 기반 — 팀 합의)
    raise NotImplementedError
