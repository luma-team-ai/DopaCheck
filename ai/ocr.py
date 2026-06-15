"""영수증 OCR 파싱 (담당: 오영석 — FR-40)."""
import base64
import json

from ai.utils import extract_json, extract_text, get_client
from config import MODEL_OCR


def _detect_media_type(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"GIF8":
        return "image/gif"
    if len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def parse_receipt(image_bytes: bytes) -> dict:
    """영수증 이미지에서 음식명·단가·수량·배달비를 추출한다. (FR-2)

    Args:
        image_bytes: 업로드된 JPG/PNG 이미지 바이트

    Returns:
        {
            "success": True,
            "items": [{"name": "후라이드치킨", "price": 18000, "quantity": 1}],
            "delivery_fee": 3000,
            "total_price": 21000
        }

    Raises:
        Exception: OCR 호출 실패 시 — 라우트에서 catch 후 수동 입력 fallback (FR-7)
    """
    media_type = _detect_media_type(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = (
        "이 배달 영수증 이미지에서 주문 내역을 추출해주세요.\n\n"
        "JSON 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '{"items": [{"name": "음식명", "price": 가격(원, 정수), "quantity": 수량(정수)}], '
        '"delivery_fee": 배달비(원, 정수), "total_price": 총금액(원, 정수)}\n\n'
        "가격이 명확하지 않으면 0으로 처리하세요."
    )

    response = get_client().messages.create(
        model=MODEL_OCR,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = extract_text(response)
    try:
        result = json.loads(extract_json(text))
    except json.JSONDecodeError as e:
        raise ValueError(f"영수증 OCR 응답 파싱 실패: {e}") from e
    return {"success": True, **result}
