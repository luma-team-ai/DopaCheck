"""공감 코멘트 생성 (담당: 오영석 — FR-42)."""
import json
import logging
import math

from ai.utils import extract_text, get_client, extract_json
from config import MODEL_COMMENT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "당신은 공감 능력이 높은 생활 습관 AI 코치입니다. "
    "사용자를 판단하거나 비판하지 않고, 따뜻하고 친근하게 한 문장으로 응답합니다."
)

# 가드 문구: LLM이 단위·기간을 임의로 바꾸거나 SNS/게임 시간을 합치지 않도록 (#211)
_GUARD = (
    "위에 주어진 수치만 사용하세요. 임의로 월간 환산하거나 기간/단위를 바꾸지 마세요. "
    "SNS 시간과 게임 시간은 별개의 값입니다."
)

_PROMPTS = {
    "delivery": (
        "사용자의 배달 분석 결과입니다:\n{context}\n\n" + _GUARD + "\n\n"
        "이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요."
    ),
    "time": (
        "사용자의 SNS·게임 시간 분석 결과입니다:\n{context}\n\n" + _GUARD + "\n\n"
        "이 결과를 보고 공감 코멘트를 한 문장으로 작성해주세요. 긍정적으로 마무리하세요."
    ),
    "report": (
        "사용자의 주간 리포트 데이터입니다:\n{context}\n\n" + _GUARD + "\n\n"
        "이번 주 노력을 인정하고 다음 주를 응원하는 공감 코멘트를 한 문장으로 작성해주세요."
    ),
}


_MAX_STR_LEN = 200  # 문자열 값 최대 길이 (프롬프트 인젝션 완화)

# 프롬프트 경계 보호: 개행/CR/탭/널바이트 제거 (#211 P2)
_STRIP_CHARS = str.maketrans({"\n": " ", "\r": " ", "\t": " ", "\x00": None})


def _sanitize_context(obj, _depth: int = 0):
    """dict/list/str 재귀 순회 — 문자열 값을 200자로 truncate한다.

    프롬프트 인젝션 완화 유틸. 라벨링 경로(_safe_str)와 별개로 유지되며,
    재귀적인 dict/list 컨텍스트를 길이 제한할 때 사용한다.
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


def _safe_str(value) -> str:
    """사용자 유래 문자열을 200자로 truncate + 개행/탭/널바이트 제거 (프롬프트 인젝션 완화)."""
    return str(value).translate(_STRIP_CHARS)[:_MAX_STR_LEN]


def _fmt_won(value) -> str:
    """원 단위 정수 천단위 콤마 포맷. 숫자(유한값)가 아니면 None."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return f"{int(round(v)):,}원"


def _fmt_h(value) -> str:
    """시간(float) 포맷. 숫자(유한값)가 아니면 None."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return f"{v:.1f}시간"


def _fmt_min_with_h(value) -> str:
    """분(int)을 '1200분(20.0시간)' 형태로 포맷. 숫자(유한값)가 아니면 None."""
    try:
        m = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(m):
        return None
    return f"{int(round(m))}분({m / 60:.1f}시간)"


def _fmt_count(value, unit: str) -> str:
    """환산 개수 포맷('20.0개' 등). 숫자(유한값)가 아니면 None."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return f"{v:.1f}{unit}"


def _build_time_context(ctx: dict) -> list:
    """time 컨텍스트 → 한국어 라벨 + 단위 라인 리스트."""
    lines = []
    sns = _fmt_h(ctx.get("sns_total_h"))
    if sns is not None:
        lines.append(f"- SNS 사용 시간(유튜브+인스타+틱톡 합): {sns}")
    parts = []
    for key, name in (("youtube_h", "유튜브"), ("instagram_h", "인스타"), ("tiktok_h", "틱톡")):
        v = _fmt_h(ctx.get(key))
        if v is not None:
            parts.append(f"{name} {v}")
    if parts:
        lines.append("- SNS 세부: " + " / ".join(parts))
    game = _fmt_h(ctx.get("game_h"))
    if game is not None:
        lines.append(f"- 게임 사용 시간: {game}")
    conv_parts = []
    for key, unit, label in (("book_n", "권", "책"), ("lecture_n", "개", "온라인 강의"), ("workout_n", "회", "운동")):
        v = _fmt_count(ctx.get(key), unit)
        if v is not None:
            conv_parts.append(f"{label} {v}")
    if conv_parts:
        lines.append("- SNS 시간으로 가능했던 것: " + " / ".join(conv_parts))
    cost = _fmt_won(ctx.get("game_cost"))
    wage = _fmt_won(ctx.get("hourly_wage"))
    if cost is not None:
        suffix = f" (시급 {wage} 기준)" if wage is not None else ""
        lines.append(f"- 게임 시간의 '주간' 기회비용: {cost}{suffix}")
    return lines


def _build_delivery_context(ctx: dict) -> list:
    """delivery 컨텍스트 → 한국어 라벨 + 단위 라인 리스트."""
    lines = []
    price = _fmt_won(ctx.get("total_price"))
    if price is not None:
        lines.append(f"- 배달 총 지출: {price}")
    kcal = ctx.get("total_kcal")
    try:
        lines.append(f"- 섭취 칼로리: {int(round(float(kcal)))}kcal")
    except (TypeError, ValueError):
        pass
    conversions = ctx.get("conversions")
    if isinstance(conversions, (list, tuple)) and conversions:
        # 사용자 유래 라벨 — 길이 제한/개행 제거
        labels = " / ".join(_safe_str(c) for c in conversions)
        lines.append(f"- 환산: {labels}")
    return lines


def _build_report_context(ctx: dict) -> list:
    """report 컨텍스트 → 한국어 라벨 + 단위 라인 리스트(분은 시간 병기)."""
    lines = []
    price = _fmt_won(ctx.get("total_price"))
    if price is not None:
        lines.append(f"- 배달 총 지출: {price}")
    cal = ctx.get("total_calories")
    try:
        lines.append(f"- 섭취 칼로리: {int(round(float(cal)))}kcal")
    except (TypeError, ValueError):
        pass
    cnt = ctx.get("delivery_count")
    try:
        lines.append(f"- 배달 횟수: {int(cnt)}건")
    except (TypeError, ValueError):
        pass
    total = _fmt_min_with_h(ctx.get("total_time_min"))
    if total is not None:
        lines.append(f"- SNS+게임 총 사용 시간: {total}")
    for key, name in (
        ("youtube_min", "유튜브"),
        ("instagram_min", "인스타"),
        ("tiktok_min", "틱톡"),
        ("game_min", "게임"),
    ):
        v = _fmt_min_with_h(ctx.get(key))
        if v is not None:
            lines.append(f"- {name} 사용 시간: {v}")
    score = ctx.get("score")
    try:
        lines.append(f"- 도파민 점수: {int(score)}/100")
    except (TypeError, ValueError):
        pass
    return lines


_CONTEXT_BUILDERS = {
    "time": _build_time_context,
    "delivery": _build_delivery_context,
    "report": _build_report_context,
}


def _format_context(comment_type: str, context: dict) -> str:
    """comment_type별로 한국어 라벨 + 단위 명시된 사람이 읽을 수 있는 컨텍스트 문자열 생성 (#211).

    raw json.dumps 대신 라벨링하여 LLM이 값의 의미·단위를 오해하지 않게 한다.
    숫자는 안전하게 포맷팅, 사용자 유래 문자열은 길이 제한/개행 제거.
    알 수 없는 type·키 누락에도 죽지 않게 .get + 폴백.
    """
    if not isinstance(context, dict):
        return _safe_str(context)
    builder = _CONTEXT_BUILDERS.get(comment_type, _build_report_context)
    lines = builder(context)
    if not lines:
        return "(데이터 없음)"
    return "\n".join(lines)


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
    # raw json.dumps 대신 라벨+단위 명시 컨텍스트 삽입 — LLM 단위 오해 방지 (#211, FR-42)
    # 숫자 포맷팅은 안전, 사용자 유래 문자열은 200자 truncate/개행 제거로 인젝션 완화
    context_str = _format_context(comment_type, context)
    prompt = template.format(context=context_str)

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
