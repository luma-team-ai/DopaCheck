"""챌린지 추천 (담당: 오영석 — FR-44)."""
import json

import anthropic

from ai.utils import extract_json

_client = anthropic.Anthropic()


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
    avg_delivery = history.get("avg_delivery_per_week", 0)
    top_app = history.get("top_app")
    top_app_hours = history.get("top_app_hours", 0)

    app_line = (
        f"- 가장 많이 쓰는 앱: {top_app} ({top_app_hours:.1f}시간/주)\n"
        if top_app
        else ""
    )
    prompt = (
        f"사용자의 최근 습관:\n"
        f"- 주간 평균 배달 횟수: {avg_delivery:.1f}회\n"
        f"{app_line}"
        "이 사용자에게 맞춤 챌린지 3개를 한국어로 추천해주세요. "
        "각 챌린지는 현실적으로 달성 가능하고 구체적이어야 합니다.\n\n"
        "JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '[{"title": "챌린지 제목", "description": "구체적인 설명", '
        '"target_type": "delivery 또는 time 또는 both", "target_value": 숫자}, ...]'
    )

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    try:
        recommendations = json.loads(extract_json(text))
    except json.JSONDecodeError as e:
        raise ValueError(f"챌린지 추천 응답 파싱 실패: {e}") from e

    return {"success": True, "recommendations": recommendations}
