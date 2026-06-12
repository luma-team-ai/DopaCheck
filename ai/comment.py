"""공감 코멘트 생성 (담당: 오영석 — FR-42)."""


def generate(type: str, context: dict) -> str:
    """분석 컨텍스트를 입력받아 LLM 공감 코멘트를 생성한다. (FR-6, FR-14, FR-17)

    Args:
        type: "delivery" | "time" | "report"
        context: 분석 결과 컨텍스트
            예: {"total_price": 21000, "total_kcal": 1940,
                 "conversions": ["치킨 1.2마리값", "러닝 28분"]}

    Returns:
        공감 코멘트 문자열
        예: "오늘도 맛있는 걸 드셨군요! 그 칼로리, 러닝 28분이면 다 태울 수 있어요."
    """
    # TODO(오영석): Claude API로 type별 프롬프트 분기 + 코멘트 생성 구현
    raise NotImplementedError
