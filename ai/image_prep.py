"""영수증 이미지 전처리 — Claude native 해상도 리사이즈 + 대비강화 (#188)."""
import math
import logging
from io import BytesIO

from PIL import Image, ImageOps, ImageEnhance

from config import OCR_MAX_EDGE, OCR_MAX_VISION_TOKENS

logger = logging.getLogger(__name__)


def count_image_tokens(width: int, height: int) -> int:
    return math.ceil(width / 28) * math.ceil(height / 28)


def resized_size(width: int, height: int, max_edge: int = 1568, max_tokens: int = 1568) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        return (max(width, 0), max(height, 0))
    def fits(w: int, h: int) -> bool:
        return (math.ceil(w / 28) * 28 <= max_edge
                and math.ceil(h / 28) * 28 <= max_edge
                and count_image_tokens(w, h) <= max_tokens)
    if fits(width, height):
        return (width, height)
    if height > width:
        rh, rw = resized_size(height, width, max_edge, max_tokens)
        return (rw, rh)
    aspect_ratio = width / height
    lo, hi = 1, width
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if fits(mid, max(round(mid / aspect_ratio), 1)):
            lo = mid
        else:
            hi = mid
    return (lo, max(round(lo / aspect_ratio), 1))


def _detect_media_type(image_bytes: bytes) -> str:
    """이미지 bytes에서 media_type 감지."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if image_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    if image_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    return "image/jpeg"


def preprocess_receipt(image_bytes: bytes) -> tuple[bytes, str]:
    """영수증 이미지를 Claude native 해상도로 사전 리사이즈 + 대비강화하여 (처리된 bytes, media_type) 반환.
    Pillow 실패/비이미지 입력 시 원본 bytes로 안전 fallback(파이프라인 비차단).
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        tw, th = resized_size(img.width, img.height, OCR_MAX_EDGE, OCR_MAX_VISION_TOKENS)
        if (tw, th) != (img.width, img.height):
            img = img.resize((tw, th), Image.LANCZOS)
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Sharpness(img).enhance(1.5)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"
    except Exception as e:
        logger.warning("preprocess_receipt 실패, 원본 반환: %s", e)
        return image_bytes, _detect_media_type(image_bytes)
