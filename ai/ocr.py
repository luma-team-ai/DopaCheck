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
        "이 영수증 이미지에서 주문한 음식 정보를 추출해주세요.\n"
        "이미지가 회전되어 있어도 올바르게 읽어주세요.\n\n"
        "【영수증 3구역 구조】\n"
        "① 상단: 가게명·주소·사업자번호·대표자·날짜 — 음식명이 아님\n"
        "② 중단: 상품명/수량/금액 테이블 — 실제 음식 정보가 여기에만 있음\n"
        "③ 하단: 공급가액·부가세·합계·결제수단·승인번호 등 — 음식명이 아님\n\n"
        "【추출 규칙】\n"
        "1. 가게명·주소·대표자·사업자번호는 음식명이 아닙니다. items에 절대 넣지 마세요.\n"
        "2. '상품명'은 ② 중단 테이블의 컬럼 헤더입니다. items에 넣지 마세요.\n"
        "3. ② 중단 상품명 컬럼의 실제 음식명(예: 돈까스, 덮밥, 치킨 등)만 items에 포함하세요.\n"
        "4. '- 세트:', '- 옵션:', '- 추가:' 등 하이픈(-)으로 시작하는 옵션 줄은 "
        "바로 위 음식명에 괄호로 합쳐주세요. 예) 돈까스(미니세트)\n"
        "5. 공급가액·부가세·합계·할인·적립금·신용카드·승인번호·가맹점 등 "
        "결제/세금 관련 항목은 items에 절대 포함하지 마세요.\n"
        "6. total_price는 '합계' 또는 '제금액' 란의 숫자를 사용하세요.\n"
        "7. 배달비(배달료) 항목이 있으면 delivery_fee에 넣고, 없으면 0으로 설정하세요.\n"
        "8. 가격이 불명확하면 0으로 처리하세요.\n\n"
        "JSON 형식으로만 응답하세요 (설명 없이):\n"
        '{"items": [{"name": "음식명(옵션)", "price": 가격(정수), "quantity": 수량(정수)}], '
        '"delivery_fee": 배달비(정수), "total_price": 총금액(정수)}'
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
    try:
        text = extract_text(response)
        result = json.loads(extract_json(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"영수증 OCR 응답 파싱 실패: {e}") from e
    return {"success": True, **result}
