"""배달 영수증 분석 (담당: 김관영 — FR-1~8)."""
import json
import logging
import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

import ai.calorie as ai_calorie
import ai.comment as ai_comment
import ai.ocr as ai_ocr
from config import (
    CHICKEN_PRICE,
    GYM_MONTHLY_PRICE,
    RUNNING_KCAL_PER_MIN,
    WALKING_KCAL_PER_HOUR,
)
from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf

logger = logging.getLogger(__name__)

delivery_bp = Blueprint("delivery", __name__, url_prefix="/delivery")

# ── 허용 MIME 유형 (FR-1) ────────────────────────────────
_ALLOWED_MIME = {"image/jpeg", "image/png"}

# 수동 입력 음식명 최대 개수 (AI 비용·지연 상한)
_MAX_FOOD_NAMES = 20


def _is_real_jpeg_or_png(image_bytes: bytes) -> bool:
    """매직 바이트로 실제 JPEG/PNG 인지 검증한다. (FR-1 — MIME 스푸핑 차단)

    클라이언트가 보내는 Content-Type(mimetype)은 위조 가능하므로 시그니처를 직접 확인한다.
    - PNG: 89 50 4E 47 0D 0A 1A 0A
    - JPEG: FF D8 FF
    """
    return (
        image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        or image_bytes[:3] == b"\xff\xd8\xff"
    )


# ── 순수 환산 함수 (FR-4, FR-5) ─────────────────────────
# 경계값 테스트 용이하도록 라우트에서 분리한다.

def calc_spending_conversion(total_price: int) -> dict:
    """지출 금액을 치킨·헬스장 단위로 환산한다. (FR-4)

    Args:
        total_price: 총 지출 (원, 0 이상 정수)

    Returns:
        {
            "chicken": float,      # 치킨 N마리 (소수점 1자리)
            "gym_months": float,   # 헬스장 N개월 (소수점 1자리)
            "chicken_label": str,  # 사람이 읽기 편한 문자열
            "gym_label": str,
        }
    """
    price = max(0, total_price)
    chicken = round(price / CHICKEN_PRICE, 1) if CHICKEN_PRICE > 0 else 0.0
    gym = round(price / GYM_MONTHLY_PRICE, 1) if GYM_MONTHLY_PRICE > 0 else 0.0
    return {
        "chicken": chicken,
        "gym_months": gym,
        "chicken_label": f"치킨 {chicken}마리 값",
        "gym_label": f"헬스장 {gym}개월 치",
    }


def calc_calorie_conversion(total_kcal: int) -> dict:
    """칼로리를 러닝·걷기 단위로 환산한다. (FR-5)

    Args:
        total_kcal: 총 칼로리 (kcal, 0 이상 정수)

    Returns:
        {
            "running_min": float,   # 러닝 N분
            "walking_hours": float, # 걷기 N시간 (소수점 1자리)
            "running_label": str,
            "walking_label": str,
        }
    """
    kcal = max(0, total_kcal)
    running_min = round(kcal / RUNNING_KCAL_PER_MIN, 1) if RUNNING_KCAL_PER_MIN > 0 else 0.0
    walking_hours = round(kcal / WALKING_KCAL_PER_HOUR, 1) if WALKING_KCAL_PER_HOUR > 0 else 0.0
    return {
        "running_min": running_min,
        "walking_hours": walking_hours,
        "running_label": f"러닝 {running_min}분",
        "walking_label": f"걷기 {walking_hours}시간",
    }


# ── 라우트 ──────────────────────────────────────────────

@delivery_bp.route("")
@login_required
def delivery_page():
    """영수증 업로드 폼. (FR-1)"""
    csrf_token = get_or_create_csrf_token()
    return render_template("delivery/index.html", csrf_token=csrf_token)


@delivery_bp.route("/manual")
@login_required
def manual_page():
    """OCR 실패 시 수동 입력 폼 fallback. (FR-7)"""
    csrf_token = get_or_create_csrf_token()
    ocr_failed = request.args.get("ocr_failed") == "1"
    return render_template("delivery/manual.html", csrf_token=csrf_token, ocr_failed=ocr_failed)


@delivery_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """영수증 분석 파이프라인.

    1. 업로드 이미지 검증 (JPG/PNG — FR-1)
    2. ai.ocr.parse_receipt() 호출 → 실패 시 수동 입력 폼 fallback (FR-2, FR-7)
    3. 사용자 확인/수정 값 기준 ai.calorie.estimate() 호출 (FR-3)
    4. 지출 환산(치킨 N마리/헬스장 N개월 — FR-4), 칼로리 환산(러닝 N분/걷기 N시간 — FR-5)
       → config.py 상수 사용
    5. ai.comment.generate("delivery", context) 호출 (FR-6)
    6. delivery_records 저장 + 도파민 점수 재산출 트리거 (FR-8, FR-31)
    """
    verify_csrf()
    user_id = session.get("user_id")  # int (BIGINT PK)
    if not user_id:
        abort(401)

    # ── 수동 입력 경로 (OCR 실패 후 사용자가 manual.html 폼 제출) ──
    if request.form.get("manual_input") == "1":
        return _handle_manual_input(user_id)

    # ── 이미지 업로드 검증 (FR-1) ──────────────────────────
    image_file = request.files.get("image")
    if not image_file or not image_file.filename:
        flash("이미지를 선택해주세요.", "error")
        return redirect(url_for("delivery.delivery_page"))

    if image_file.mimetype not in _ALLOWED_MIME:
        flash("JPG 또는 PNG 파일만 업로드 가능합니다.", "error")
        return redirect(url_for("delivery.delivery_page"))

    image_bytes = image_file.read()

    # 매직 바이트 검증 — mimetype 위조 차단 (FR-1)
    if not _is_real_jpeg_or_png(image_bytes):
        flash("올바른 JPG/PNG 이미지가 아닙니다.", "error")
        return redirect(url_for("delivery.delivery_page"))

    # ── OCR (FR-2) ─────────────────────────────────────────
    try:
        ocr_result = ai_ocr.parse_receipt(image_bytes)
        items = ocr_result.get("items", [])
        delivery_fee = int(ocr_result.get("delivery_fee") or 0)
        total_price = int(ocr_result.get("total_price") or 0)
    except Exception as e:
        logger.warning("OCR 실패 — fallback 수동 입력 폼으로 전환: %s", e)
        flash("영수증 인식에 실패했습니다. 직접 입력해주세요.", "warning")
        return redirect(url_for("delivery.manual_page", ocr_failed=1))

    # OCR 결과 0원 — 영수증이 아닌 이미지일 가능성이 높으므로 수동 입력으로 전환
    if total_price == 0:
        flash("금액을 인식하지 못했습니다. 직접 입력해주세요.", "warning")
        return redirect(url_for("delivery.manual_page", ocr_failed=1))

    # ── 칼로리 추론 이후 공통 파이프라인 (FR-3~8) ─────────────
    food_names = [it["name"] for it in items if isinstance(it, dict) and it.get("name")]
    return _finalize_delivery(user_id, items, total_price, delivery_fee, food_names)


def _handle_manual_input(user_id: int):
    """수동 입력 폼 제출 처리 — OCR fallback (FR-7).

    폼 필드:
      - food_names: 쉼표 구분 음식명 문자열
      - total_price: 총 금액 (원)
      - delivery_fee: 배달비 (원)
    """
    if not user_id:
        abort(401)
    raw_names = request.form.get("food_names", "")
    food_names = [n.strip()[:100] for n in raw_names.split(",") if n.strip()][:_MAX_FOOD_NAMES]

    # 음식명 필수 검증 (FR-7)
    if not food_names:
        flash("음식명을 1개 이상 입력해주세요.", "error")
        return redirect(url_for("delivery.manual_page"))

    try:
        total_price = int(request.form.get("total_price") or 0)
    except (ValueError, TypeError):
        flash("총 금액을 올바르게 입력해주세요.", "error")
        return redirect(url_for("delivery.manual_page"))

    if total_price < 0:
        flash("총 금액은 0원 이상이어야 합니다.", "error")
        return redirect(url_for("delivery.manual_page"))

    # 배달비는 보조 메타데이터 — total_price(핵심 지출)와 달리 음수/비정수는
    # 거부 대신 0으로 무음 보정한다(사용자 흐름 차단 최소화).
    try:
        delivery_fee = int(request.form.get("delivery_fee") or 0)
        if delivery_fee < 0:
            delivery_fee = 0
    except (ValueError, TypeError):
        delivery_fee = 0

    items = [{"name": n, "price": 0, "quantity": 1} for n in food_names]
    return _finalize_delivery(
        user_id, items, total_price, delivery_fee, food_names,
        error_redirect="delivery.manual_page",
    )


def _finalize_delivery(
    user_id: int,
    items: list,
    total_price: int,
    delivery_fee: int,
    food_names: list,
    error_redirect: str = "delivery.delivery_page",
):
    """칼로리추론 → 환산 → 코멘트 → DB저장 → 점수재산출 → result.html 렌더링. (FR-3~8)"""
    # ── 칼로리 추론 (FR-3) ─────────────────────────────────
    total_kcal = 0
    calories = []
    try:
        cal_result = ai_calorie.estimate(food_names)
        calories = cal_result.get("calories", [])
        total_kcal = int(cal_result.get("total_kcal") or 0)
    except Exception as e:
        logger.warning("칼로리 추론 실패 — 부분 결과로 진행: %s", e)

    # ── 환산 (FR-4, FR-5) ──────────────────────────────────
    spending_conv = calc_spending_conversion(total_price)
    calorie_conv = calc_calorie_conversion(total_kcal)
    conversions = [spending_conv["chicken_label"], calorie_conv["running_label"]]

    # ── 공감 코멘트 (FR-6) ─────────────────────────────────
    comment = ""
    try:
        context = {
            "total_price": total_price,
            "total_kcal": total_kcal,
            "conversions": conversions,
        }
        comment = ai_comment.generate("delivery", context)
    except Exception as e:
        logger.warning("코멘트 생성 실패 — 빈 문자열로 진행: %s", e)

    # ── DB 저장 (FR-8) ─────────────────────────────────────
    record_id = str(uuid.uuid4())
    try:
        with db() as cursor:
            cursor.execute(
                "INSERT INTO delivery_records"
                " (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    record_id,
                    user_id,
                    total_price,
                    delivery_fee,
                    total_kcal,
                    json.dumps(items, ensure_ascii=False),
                    comment,
                ),
            )
    except Exception as e:
        logger.error("delivery_records 저장 실패: %s", e)
        flash("결과 저장에 실패했습니다. 잠시 후 다시 시도해주세요.", "error")
        return redirect(url_for(error_redirect))

    # ── 도파민 점수 재산출 트리거 (FR-8, FR-31) ──────────────
    try:
        from services.score_service import recalculate_score
        recalculate_score(user_id)
    except NotImplementedError:
        pass  # 점수 라우트 미구현 단계에서는 무시
    except Exception as e:
        logger.warning("도파민 점수 재산출 실패 (비치명적): %s", e)

    return render_template(
        "delivery/result.html",
        items=items,
        calories=calories,
        total_price=total_price,
        delivery_fee=delivery_fee,
        total_kcal=total_kcal,
        spending_conv=spending_conv,
        calorie_conv=calorie_conv,
        comment=comment,
    )
