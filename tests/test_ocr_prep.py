"""tests/test_ocr_prep.py — OCR 이미지 전처리 및 파라미터 검증 (#188)"""
from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw

from ai.image_prep import count_image_tokens, resized_size, preprocess_receipt


# ── resized_size 단위 테스트 ──────────────────────────────

def test_resized_size_official_example():
    """공식 Anthropic 예시: 1075×1520 → 924×1307.

    출처: platform.claude.com/docs vision — "How Claude resizes and pads images"
    (sonnet급 native = long edge 1568px + 비전타일 1568). #188 PR.
    """
    result = resized_size(1075, 1520)
    assert result == (924, 1307), f"expected (924, 1307), got {result}"


def test_resized_size_large_landscape():
    """가로 대형 이미지도 native 이하로 축소"""
    w, h = resized_size(4000, 2000)
    assert count_image_tokens(w, h) <= 1568
    import math
    assert math.ceil(w / 28) * 28 <= 1568
    assert math.ceil(h / 28) * 28 <= 1568


def test_resized_size_small_image_unchanged():
    """이미 작은 이미지는 그대로 반환(업스케일 없음)"""
    assert resized_size(800, 600) == (800, 600)


# ── preprocess_receipt 단위 테스트 ──────────────────────

def _make_image_bytes(width=3000, height=2000) -> bytes:
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Receipt Test 영수증", fill="black")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_preprocess_large_image_shrinks():
    """대형 이미지가 native 이하로 줄어들고 PNG 반환"""
    raw = _make_image_bytes(3000, 2000)
    result_bytes, media_type = preprocess_receipt(raw)

    assert media_type == "image/png"
    out = Image.open(BytesIO(result_bytes))
    assert out.width <= 1568
    assert out.height <= 1568
    assert count_image_tokens(out.width, out.height) <= 1568


def test_preprocess_fallback_on_invalid_bytes():
    """손상 바이트 입력 시 원본 bytes fallback"""
    bad = b"notimage"
    result_bytes, media_type = preprocess_receipt(bad)
    assert result_bytes == bad  # 원본 그대로


# ── parse_receipt 파라미터 검증 ──────────────────────────

def test_parse_receipt_calls_with_correct_params():
    """parse_receipt가 temperature=0, max_tokens=2048로 Claude API 호출하는지 검증"""
    from ai.ocr import parse_receipt
    from config import OCR_TEMPERATURE, OCR_MAX_OUTPUT_TOKENS

    dummy_bytes = _make_image_bytes(100, 200)  # 소형 → fallback 없이 처리

    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = '{"items":[],"delivery_fee":0,"total_price":10000}'

    mock_msg = MagicMock()
    mock_msg.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg

    with patch("ai.ocr._client", mock_client):
        parse_receipt(dummy_bytes)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs.get("temperature") == OCR_TEMPERATURE, (
        f"temperature가 {OCR_TEMPERATURE}이어야 하는데 {call_kwargs.get('temperature')}임"
    )
    assert call_kwargs.get("max_tokens") == OCR_MAX_OUTPUT_TOKENS, (
        f"max_tokens가 {OCR_MAX_OUTPUT_TOKENS}이어야 하는데 {call_kwargs.get('max_tokens')}임"
    )
