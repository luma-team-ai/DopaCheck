"""칼로리 추론 (담당: 오영석 — FR-41)."""


def estimate(items: list[str]) -> dict:
    """음식명 배열을 입력받아 LLM으로 칼로리를 추론한다. (FR-3)

    Args:
        items: 음식명 리스트 (예: ["후라이드치킨", "콜라"])

    Returns:
        {
            "success": True,
            "calories": [
                {"name": "후라이드치킨", "kcal": 1800},
                {"name": "콜라", "kcal": 140}
            ],
            "total_kcal": 1940
        }
    """
    # TODO(오영석): Claude API로 음식명 → kcal 추론 구현
    raise NotImplementedError
