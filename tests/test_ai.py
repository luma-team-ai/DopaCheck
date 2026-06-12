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
    with patch("ai.ocr._client") as mock_client:
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
    with patch("ai.calorie._client") as mock_client:
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
        with patch("ai.comment._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(expected)
            result = generate(comment_type, {"total_price": 21000, "total_kcal": 1940})

        assert isinstance(result, str)
        assert len(result) > 0
