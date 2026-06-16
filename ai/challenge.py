"""챌린지 추천 (담당: 오영석 — FR-44)."""
import json

from ai.utils import extract_json, extract_text, get_client
from config import MODEL_CHALLENGE


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
        "target_value 및 description 규칙 (반드시 준수):\n"
        "- delivery 타입: target_value는 주간 배달 목표 횟수(양의 정수, 예: 2, 3). "
        "description에 줄여야 할 배달 횟수를 명시.\n"
        "- time 타입: target_value는 주간 앱 사용 목표 시간을 반드시 분(minutes) 단위 정수로 설정 "
        "(예: 1시간 → 60, 5시간 → 300). description에 '주 X분 이하로 줄이기' 형태로 명시.\n"
        "- both 타입: target_value는 배달 횟수와 앱 사용 시간(시간 단위) 공통 목표값(양의 정수, 예: 3이면 배달 3회 이하 & 앱 3시간 이하). "
        "description에 반드시 배달 목표 횟수(N회)와 앱 사용 목표 시간(N시간) 두 가지를 모두 명시.\n\n"
        "JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '[{"title": "챌린지 제목", "description": "구체적인 설명", '
        '"target_type": "delivery 또는 time 또는 both", "target_value": 숫자}, ...]'
    )

    response = get_client().messages.create(
        model=MODEL_CHALLENGE,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        text = extract_text(response)
        recommendations = json.loads(extract_json(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"챌린지 추천 응답 파싱 실패: {e}") from e

    for rec in recommendations:
        tt = rec.get("target_type", "")
        try:
            tv = float(rec.get("target_value", 1))
        except (TypeError, ValueError):
            tv = 1.0
        if tt == "time":
            # AI가 시간(hours) 단위로 반환하면 분으로 변환 (100분 이하이면 시간으로 판단)
            if tv < 100:
                tv = tv * 60
            rec["target_value"] = max(1, int(round(tv)))
        else:
            # delivery / both: 정수 횟수
            rec["target_value"] = max(1, int(round(tv)))

    return {"success": True, "recommendations": recommendations}
