"""챌린지 추천 (담당: 오영석 — FR-44)."""


def recommend(history: dict) -> dict:
    """사용자 히스토리 기반 맞춤 챌린지를 추천한다. (FR-33)

    Args:
        history: {
            "avg_delivery_per_week": 3.2,
            "top_app": "youtube",
            "top_app_hours": 6.5
        }

    Returns:
        {
            "success": True,
            "recommendations": [
                {
                    "title": "이번 주 배달 2회 이하",
                    "description": "평소보다 1.2회 줄여보세요!",
                    "target_type": "delivery",   # "delivery" | "time" | "both"
                    "target_value": 2
                }
            ]
        }
    """
    # TODO(오영석): Claude API로 히스토리 기반 챌린지 추천 구현
    raise NotImplementedError
