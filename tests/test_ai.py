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


def test_도파민_점수_계산():
    """FR-39: 도파민 점수 규칙 기반 계산 (경계값 포함)."""
    from ai.score import calculate

    # 최고점: 배달 0원, 스크린타임 0분, 챌린지 4개 완료
    result_max = calculate({"delivery_total": 0, "time_total_min": 0, "challenge_completed": 4})
    assert result_max["score"] == 100
    assert result_max["delivery_contribution"] == 40
    assert result_max["time_contribution"] == 40
    assert result_max["challenge_bonus"] == 20

    # 최저점: 배달 200000원 이상, 스크린타임 2100분 이상, 챌린지 0개
    result_min = calculate({"delivery_total": 200_000, "time_total_min": 2_100, "challenge_completed": 0})
    assert result_min["score"] == 0
    assert result_min["delivery_contribution"] == 0
    assert result_min["time_contribution"] == 0
    assert result_min["challenge_bonus"] == 0

    # 중간값: 배달 100000원, 스크린타임 1050분, 챌린지 2개
    result_mid = calculate({"delivery_total": 100_000, "time_total_min": 1_050, "challenge_completed": 2})
    assert result_mid["delivery_contribution"] == 20
    assert result_mid["time_contribution"] == 20
    assert result_mid["challenge_bonus"] == 10
    assert result_mid["score"] == 50


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
