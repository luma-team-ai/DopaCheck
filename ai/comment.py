"""공감 코멘트 생성 (담당: 오영석 — FR-42)."""
import json
import logging

from ai.utils import extract_text, get_client, extract_json
from config import MODEL_COMMENT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "당신은 공감 능력이 높은 생활 습관 AI 코치입니다. "
    "사용자를 판단하거나 비판하지 않고, 따뜻하고 친근하게 한 문장으로 응답합니다."
)

_PROMPTS = {
    "delivery": "사용자의 배달 분석 결과입니다: {context}\n\n이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요.",
    "time": "사용자의 SNS·게임 시간 분석 결과입니다: {context}\n\n이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요.",
    "report": "사용자의 주간 리포트 데이터입니다: {context}\n\n이번 주 노력을 인정하고 다음 주를 응원하는 공감 코멘트를 한 문장으로 작성해주세요.",
}


_MAX_STR_LEN = 200  # 문자열 값 최대 길이 (프롬프트 인젝션 완화)


def _sanitize_context(obj, _depth: int = 0):
    """dict/list/str 재귀 순회 — 문자열 값을 200자로 truncate한다.

    프롬프트 인젝션 완화: 사용자 입력이 섞인 컨텍스트를 LLM에 직접 삽입하기 전에
    모든 문자열 리프 값을 길이 제한 후 json.dumps로 직렬화한다.
    """
    if _depth > 10:
        return str(obj)[:_MAX_STR_LEN]
    if isinstance(obj, dict):
        return {k: _sanitize_context(v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_context(v, _depth + 1) for v in obj]
    if isinstance(obj, str):
        return obj[:_MAX_STR_LEN]
    return obj


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
    # 프롬프트 인젝션 완화: dict를 JSON 직렬화 + 문자열 값 200자 truncate (FR-42)
    safe_context = _sanitize_context(context)
    prompt = template.format(context=json.dumps(safe_context, ensure_ascii=False))

    response = get_client().messages.create(
        model=MODEL_COMMENT,
        max_tokens=256,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return extract_text(response).strip()
    except ValueError as e:
        raise ValueError(f"공감 코멘트 응답에 text 블록이 없습니다: {e}") from e


_TIP_SYSTEM = (
    "당신은 사용자의 도파민 자제력을 개선하고 건강한 습관을 제안하는 전문 AI 코치입니다. "
    "사용자의 도파민 점수와 이번 주 소비 패턴을 바탕으로, 실천하기 쉬운 맞춤형 '도파민 자제 팁'을 1개 제공합니다. "
    "title은 10자 이내, content는 80자 이내로 간결하게 작성하세요. "
    "응답은 반드시 아래 JSON 형식으로만 반환해야 하며, 다른 텍스트는 일절 포함하지 마십시오.\n"
    "{\n"
    "  \"title\": \"팁 제목 (예: 알림 다이어트, 주말 디지털 디톡스 등)\",\n"
    "  \"content\": \"팁 상세 내용 (실천할 수 있는 구체적이고 설득력 있는 방법 제언, 80자 이내)\"\n"
    "}"
)


def generate_tip(score: int, avg_min: int, delivery_total: int) -> dict:
    """사용자의 도파민 자제 지표를 기반으로 AI 맞춤형 실천 팁을 생성한다.

    Args:
        score: 도파민 점수
        avg_min: 이번 주 SNS·게임 시간 (분)
        delivery_total: 이번 주 배달 총 지출 (원)

    Returns:
        {"title": "팁 제목", "content": "팁 내용"}
    """
    logger.info("AI 맞춤 팁 생성 시작: score=%d, avg_min=%d, delivery_total=%d", score, avg_min, delivery_total)

    prompt = (
        f"사용자의 현재 도파민 상태 데이터입니다:\n"
        f"- 도파민 점수: {score}/100\n"
        f"- 이번 주 SNS·게임 사용 시간: {avg_min}분\n"
        f"- 이번 주 배달 지출 총액: {delivery_total}원\n\n"
        f"이 유저에게 가장 도움이 될 만한 도파민 자제 팁을 1개 제안해주세요. "
        f"점수가 높을수록(도파민 과다) 적극적인 행동 교정을, 점수가 낮을수록 현재 상태 유지를 독려하는 팁을 작성해주세요. "
        f"출력은 약속된 JSON 포맷으로만 응답해야 합니다."
    )

    default_tip = {
        "title": "알림 다이어트",
        "content": "밤 11시 이후 SNS 알림을 꺼보세요. 취침 전 무분별한 스크롤링은 다음 날 도파민 수용체 감도를 낮추어 불필요한 과소비를 조장할 수 있습니다."
    }

    try:
        response = get_client().messages.create(
            model=MODEL_COMMENT,
            max_tokens=512,
            system=_TIP_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = extract_text(response).strip()
        json_str = extract_json(raw_text)
        data = json.loads(json_str)

        if "title" in data and "content" in data:
            logger.info("AI 팁 생성 성공: title=%s", data["title"])
            return data

        logger.warning("AI 응답에 필수 필드 누락 — 기본 팁 반환")
        return default_tip
    except Exception as e:
        logger.exception("AI 팁 생성 실패 — 기본 팁 반환: %s", e)
        return default_tip
