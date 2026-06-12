"""칼로리 추론 (담당: 오영석 — FR-41)."""
import json

import anthropic

from ai.utils import extract_json

_client = anthropic.Anthropic()


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
    if not items:
        return {"success": True, "calories": [], "total_kcal": 0}

    food_list = ", ".join(items)
    prompt = (
        f"다음 음식들의 칼로리를 1인분 기준으로 추정해주세요: {food_list}\n\n"
        "JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '[{"name": "음식명", "kcal": 정수}, ...]'
    )

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    try:
        calories = json.loads(extract_json(text))
    except json.JSONDecodeError as e:
        raise ValueError(f"칼로리 추론 응답 파싱 실패: {e}") from e
    total_kcal = sum(item["kcal"] for item in calories)

    return {"success": True, "calories": calories, "total_kcal": total_kcal}
