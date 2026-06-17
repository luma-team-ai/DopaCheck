"""AI 모듈 테스트 (담당: 오영석)."""
import json
from unittest.mock import MagicMock, patch


def _mock_response(text: str):
    """anthropic 응답 mock 객체 생성."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_ocr_샘플_영수증_파싱():
    """FR-40: 영수증 이미지 → 주문 내역 파싱."""
    from ai.ocr import parse_receipt

    payload = {
        "items": [{"name": "후라이드치킨", "price": 18000, "quantity": 1}],
        "delivery_fee": 3000,
        "total_price": 21000,
    }
    # get_client()가 반환하는 싱글턴을 패치
    with patch("ai.utils._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(json.dumps(payload))
        result = parse_receipt(b"\xff\xd8\xff" + b"\x00" * 64)  # dummy JPEG

    assert result["success"] is True
    assert result["items"][0]["name"] == "후라이드치킨"
    assert result["items"][0]["price"] == 18000
    assert result["delivery_fee"] == 3000
    assert result["total_price"] == 21000


def test_칼로리_추론():
    """FR-41: 음식명 리스트 → 칼로리 추론."""
    from ai.calorie import estimate

    payload = [
        {"name": "후라이드치킨", "kcal": 1800},
        {"name": "콜라", "kcal": 140},
    ]
    with patch("ai.utils._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(json.dumps(payload))
        result = estimate(["후라이드치킨", "콜라"])

    assert result["success"] is True
    assert len(result["calories"]) == 2
    assert result["total_kcal"] == 1940
    assert result["calories"][0]["name"] == "후라이드치킨"


def test_공감_코멘트_생성():
    """FR-42: type별(delivery/time/report) 코멘트 생성."""
    from ai.comment import generate

    expected = "오늘도 맛있는 걸 드셨군요! 러닝 28분이면 다 태울 수 있어요."

    for comment_type in ("delivery", "time", "report"):
        with patch("ai.utils._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(expected)
            result = generate(comment_type, {"total_price": 21000, "total_kcal": 1940})

        assert isinstance(result, str)
        assert len(result) > 0


def _captured_prompt(comment_type: str, context: dict) -> str:
    """generate 호출 시 LLM messages content에 실제로 전달된 프롬프트 문자열을 반환."""
    from ai.comment import generate

    with patch("ai.utils._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("코멘트")
        generate(comment_type, context)
        _, kwargs = mock_client.messages.create.call_args
    return kwargs["messages"][0]["content"]


def test_time_컨텍스트_라벨_단위_가드_포함():
    """#211: time 프롬프트에 한국어 라벨·단위·가드 문구가 들어가고 SNS/게임이 별개 라인."""
    context = {
        "youtube_h": 20.0,
        "instagram_h": 15.0,
        "tiktok_h": 5.0,
        "game_h": 20.0,
        "sns_total_h": 40.0,
        "book_n": 0.0,
        "lecture_n": 20.0,
        "workout_n": 40.0,
        "game_cost": 260000,
        "hourly_wage": 13000,
    }
    prompt = _captured_prompt("time", context)

    # 라벨/단위
    assert "게임 사용 시간" in prompt
    assert "SNS" in prompt
    assert "시간" in prompt
    assert "원" in prompt
    # 가드 문구
    assert "SNS 시간과 게임 시간은 별개의 값입니다" in prompt
    assert "임의로 월간 환산하거나" in prompt
    # raw JSON 영문 키가 그대로 덤프되지 않음
    assert "sns_total_h" not in prompt
    assert "game_cost" not in prompt
    # SNS 시간과 게임 시간이 별개 라인
    sns_line = next(l for l in prompt.splitlines() if l.startswith("- SNS 사용 시간"))
    game_line = next(l for l in prompt.splitlines() if l.startswith("- 게임 사용 시간"))
    assert sns_line != game_line
    assert "40.0시간" in sns_line   # SNS만 40시간
    assert "20.0시간" in game_line  # 게임 20시간
    # 주간 기회비용 — 천단위 콤마, 월간 왜곡 없음
    assert "260,000원" in prompt
    assert "주간" in prompt


def test_report_분값_시간_병기():
    """#211: report의 분(min) 값은 '1200분(20.0시간)' 형태로 시간 병기."""
    context = {
        "total_price": 50000,
        "total_calories": 3000,
        "delivery_count": 3,
        "total_time_min": 1200,
        "youtube_min": 600,
        "instagram_min": 0,
        "tiktok_min": 0,
        "game_min": 600,
        "score": 70,
    }
    prompt = _captured_prompt("report", context)
    assert "1200분(20.0시간)" in prompt
    assert "게임 사용 시간: 600분(10.0시간)" in prompt
    assert "70/100" in prompt
    assert "SNS 시간과 게임 시간은 별개의 값입니다" in prompt


def test_delivery_conversions_길이제한_적용():
    """#211: delivery conversions(사용자 유래 문자열)는 200자 truncate/개행 제거."""
    context = {
        "total_price": 21000,
        "total_kcal": 1940,
        "conversions": ["치킨 1.2마리값", "X" * 500 + "\n악성"],
    }
    prompt = _captured_prompt("delivery", context)
    assert "치킨 1.2마리값" in prompt
    assert "21,000원" in prompt
    # 500자 입력이 200자로 잘림
    assert "X" * 500 not in prompt
    assert "X" * 200 in prompt
    # 개행 제거 — 프롬프트 라인 구조 보호
    assert "\n악성" not in prompt


def test_키_누락_빈컨텍스트_죽지_않음():
    """#211: 키 누락/빈 dict/알 수 없는 type에도 죽지 않고 폴백."""
    # 빈 컨텍스트
    prompt_empty = _captured_prompt("time", {})
    assert "(데이터 없음)" in prompt_empty
    # 알 수 없는 type → report 폴백, 키 일부만
    prompt_unknown = _captured_prompt("mystery", {"total_price": 10000})
    assert "10,000원" in prompt_unknown


def test_도파민_점수_계산():
    """FR-39: 도파민 점수 규칙 기반 계산 (경계값 포함) — 점수 반전 후 (높을수록 위험)."""
    from ai.score import calculate

    # 위험 없음: 배달 0원, 스크린타임 0분, 챌린지 4개 달성 → 0 + 0 + (-20) → clamp → 0
    result_safe = calculate({"delivery_total": 0, "time_total_min": 0, "challenge_completed": 4})
    assert result_safe["score"] == 0
    assert result_safe["delivery_contribution"] == 0
    assert result_safe["time_contribution"] == 0
    assert result_safe["challenge_bonus"] == -20

    # 최고 위험: 배달 200000원, 스크린타임 2100분, 챌린지 0개 → 40 + 40 + 0 = 80
    result_max = calculate({"delivery_total": 200_000, "time_total_min": 2_100, "challenge_completed": 0})
    assert result_max["score"] == 80
    assert result_max["delivery_contribution"] == 40
    assert result_max["time_contribution"] == 40
    assert result_max["challenge_bonus"] == 0

    # 중간값: 배달 100000원, 스크린타임 1050분, 챌린지 2개 → 20 + 20 + (-10) = 30
    result_mid = calculate({"delivery_total": 100_000, "time_total_min": 1_050, "challenge_completed": 2})
    assert result_mid["delivery_contribution"] == 20
    assert result_mid["time_contribution"] == 20
    assert result_mid["challenge_bonus"] == -10
    assert result_mid["score"] == 30


def test_챌린지_추천():
    """FR-44: 히스토리 기반 챌린지 추천 (mock LLM)."""
    from ai.challenge import recommend

    payload = [
        {
            "title": "이번 주 배달 2회 이하",
            "description": "평소보다 1.2회 줄여보세요!",
            "target_type": "delivery",
            "target_value": 2,
        },
        {
            "title": "유튜브 하루 1시간 이하",
            "description": "주간 7시간 사용을 줄여보세요.",
            "target_type": "time",
            "target_value": 60,
        },
        {
            "title": "배달+SNS 동시 줄이기",
            "description": "두 가지 모두 10% 줄여보세요.",
            "target_type": "both",
            "target_value": 0,
        },
    ]
    with patch("ai.utils._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(json.dumps(payload))
        result = recommend(
            {
                "avg_delivery_per_week": 3.2,
                "top_app": "youtube",
                "top_app_hours": 6.5,
            }
        )

    assert result["success"] is True
    assert len(result["recommendations"]) == 3
    assert result["recommendations"][0]["title"] == "이번 주 배달 2회 이하"
    assert result["recommendations"][0]["target_type"] == "delivery"


def _recommend_time_value(raw_value):
    """time 타입 추천 1건을 mock 응답으로 흘려보내고 정규화된 target_value를 반환한다."""
    from ai.challenge import recommend

    payload = [{
        "title": "유튜브 줄이기",
        "description": "주간 사용 시간을 줄여보세요.",
        "target_type": "time",
        "target_value": raw_value,
    }]
    with patch("ai.utils._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(json.dumps(payload))
        result = recommend({"avg_delivery_per_week": 1.0})
    return result["recommendations"][0]["target_value"]


def test_time_정상_분값_오염되지_않음():
    """#161 P2: 60·90분 등 정상 분 값은 그대로 유지(기존 *60 오염 회귀 방지)."""
    assert _recommend_time_value(60) == 60     # 과거: 3600 으로 오염
    assert _recommend_time_value(90) == 90     # 과거: 5400 으로 오염
    assert _recommend_time_value(300) == 300


def test_time_시간_오기입은_분으로_보정():
    """임계값(20) 미만이면 시간 오기입으로 보고 ×60 보정."""
    assert _recommend_time_value(5) == 300     # 5시간 → 300분
    assert _recommend_time_value(10) == 600    # 10시간 → 600분


def test_time_경계값_20은_분으로_신뢰():
    """임계값 경계(20)는 분으로 신뢰 — 보정하지 않음."""
    assert _recommend_time_value(20) == 20


# ── P2 추가 테스트 ────────────────────────────────────────

def test_AI_클라이언트_타임아웃_설정():
    """get_client()가 반환하는 클라이언트에 timeout이 설정되어 있다."""
    import anthropic
    from unittest.mock import patch
    from config import AI_REQUEST_TIMEOUT

    # 싱글턴 초기화를 위해 _client 를 None으로 리셋
    import ai.utils as ai_utils
    original = ai_utils._client
    ai_utils._client = None

    try:
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            ai_utils.get_client()
            mock_cls.assert_called_once_with(timeout=AI_REQUEST_TIMEOUT)
    finally:
        # 테스트 후 원래 상태 복원
        ai_utils._client = original


def test_AI_클라이언트_싱글턴():
    """get_client()를 두 번 호출해도 같은 인스턴스를 반환한다."""
    import ai.utils as ai_utils

    # 싱글턴 초기화
    ai_utils._client = None
    with patch("ai.utils.anthropic.Anthropic") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        c1 = ai_utils.get_client()
        c2 = ai_utils.get_client()
        assert c1 is c2
        assert mock_cls.call_count == 1  # 한 번만 생성
    ai_utils._client = None
