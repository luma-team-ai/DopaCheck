"""영수증 OCR 파싱 (담당: 오영석 — FR-40)."""


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
    # TODO(오영석): Claude API vision으로 영수증 파싱 구현
    raise NotImplementedError
