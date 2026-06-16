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

    return {"success": True, "recommendations": recommendations}


def suggest_new_challenges(existing: list[dict]) -> list[dict]:
    """관리자용: 기존 챌린지 참여율을 참고해 새 챌린지 3개를 추천한다."""
    lines = []
    for c in existing:
        cnt = int(c.get("participant_count") or 0)
        if cnt >= 10:
            pop = f"인기 ({cnt}명 참여)"
        elif cnt >= 3:
            pop = f"보통 ({cnt}명 참여)"
        else:
            pop = f"저조 ({cnt}명 참여)"
        lines.append(f"- {c['title']} [{pop}]")
    existing_str = "\n".join(lines) if lines else "없음"
    prompt = (
        f"현재 등록된 챌린지와 사용자 참여 현황:\n{existing_str}\n\n"
        "위 챌린지들과 겹치지 않는 새로운 챌린지 3개를 한국어로 추천해주세요.\n"
        "참여율이 높은 챌린지(인기)의 특성(구체성·달성 난이도 등)을 참고하여 "
        "더 많은 사용자가 참여할 것 같은 챌린지를 만들어 주세요.\n"
        "도파민 절제를 목표로 배달앱 사용 줄이기 또는 SNS·게임 시간 줄이기 주제여야 합니다.\n"
        "각 챌린지는 현실적이고 구체적인 목표값을 가져야 합니다.\n\n"
        "JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '[{"title": "제목", "description": "구체적인 설명", '
        '"target_type": "delivery 또는 time 또는 both", "target_value": 숫자}, ...]'
    )
    response = get_client().messages.create(
        model=MODEL_CHALLENGE,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    _VALID_TYPES = frozenset({"delivery", "time", "both"})
    try:
        text = extract_text(response)
        items = json.loads(extract_json(text))
        if not isinstance(items, list):
            raise ValueError("응답이 배열이 아닙니다")
        validated = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            target_type = str(item.get("target_type") or "").strip()
            try:
                target_value = max(0, int(float(item.get("target_value") or 0)))
            except (ValueError, TypeError):
                target_value = 0
            if not title or target_type not in _VALID_TYPES:
                continue
            validated.append({
                "title": title,
                "description": description,
                "target_type": target_type,
                "target_value": target_value,
            })
        return validated
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"AI 챌린지 추천 응답 파싱 실패: {e}") from e
