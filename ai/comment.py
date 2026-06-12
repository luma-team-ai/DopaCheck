"""공감 코멘트 생성 (담당: 오영석 — FR-42)."""
import anthropic

_client = anthropic.Anthropic()

_SYSTEM = (
    "당신은 공감 능력이 높은 생활 습관 AI 코치입니다. "
    "사용자를 판단하거나 비판하지 않고, 따뜻하고 친근하게 한 문장으로 응답합니다."
)

_PROMPTS = {
    "delivery": "사용자의 배달 분석 결과입니다: {context}\n\n이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요.",
    "time": "사용자의 SNS·게임 시간 분석 결과입니다: {context}\n\n이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요.",
    "report": "사용자의 주간 리포트 데이터입니다: {context}\n\n이번 주 노력을 인정하고 다음 주를 응원하는 공감 코멘트를 한 문장으로 작성해주세요.",
}


def generate(comment_type: str, context: dict) -> str:
    """분석 컨텍스트를 입력받아 LLM 공감 코멘트를 생성한다. (FR-6, FR-14, FR-17)

    Args:
        comment_type: "delivery" | "time" | "report"
        context: 분석 결과 컨텍스트
            예: {"total_price": 21000, "total_kcal": 1940,
                 "conversions": ["치킨 1.2마리값", "러닝 28분"]}

    Returns:
        공감 코멘트 문자열
        예: "오늘도 맛있는 걸 드셨군요! 그 칼로리, 러닝 28분이면 다 태울 수 있어요."
    """
    template = _PROMPTS.get(comment_type, _PROMPTS["report"])
    prompt = template.format(context=context)

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=256,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in response.content if b.type == "text").strip()
