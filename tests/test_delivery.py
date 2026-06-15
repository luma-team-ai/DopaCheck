"""배달 분석 테스트 (담당: 김관영)."""
import io
import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import HTTPException

from routes.delivery import _handle_manual_input, calc_calorie_conversion, calc_spending_conversion


# ── 헬퍼 ────────────────────────────────────────────────

def _make_db_mock(fetchone=None, fetchall=None):
    """db() 컨텍스트매니저 mock — cursor 반환값 지정."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone
    mock_cursor.fetchall.return_value = fetchall if fetchall is not None else []

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


def _png_bytes() -> bytes:
    """유효한 1×1 PNG 바이트 (실제 AI 호출 없이 파일 검증 통과용)."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


_OCR_OK = {
    "success": True,
    "items": [
        {"name": "후라이드치킨", "price": 18000, "quantity": 1},
        {"name": "콜라", "price": 3000, "quantity": 1},
    ],
    "delivery_fee": 3000,
    "total_price": 21000,
}

_CAL_OK = {
    "success": True,
    "calories": [
        {"name": "후라이드치킨", "kcal": 1800},
        {"name": "콜라", "kcal": 140},
    ],
    "total_kcal": 1940,
}

_COMMENT_OK = "오늘도 맛있는 걸 드셨군요! 건강도 챙겨보세요."


# ── 기본 렌더링 테스트 ────────────────────────────────────

def test_업로드_폼_렌더링(logged_in_client):
    """GET /delivery → 200"""
    assert logged_in_client.get("/delivery").status_code == 200


def test_수동입력_폼_렌더링(logged_in_client):
    """GET /delivery/manual → 200 (FR-7)"""
    assert logged_in_client.get("/delivery/manual").status_code == 200


# ── 환산 함수 단위 테스트 (FR-4, FR-5) ──────────────────

class TestCalcSpendingConversion:
    """calc_spending_conversion 경계값 테스트."""

    def test_정상값(self):
        result = calc_spending_conversion(21000)
        # CHICKEN_PRICE=20000 → 21000/20000 = 1.05 → round 1자리 = 1.0 or 1.1
        assert result["chicken"] == round(21000 / 20000, 1)
        assert result["gym_months"] == round(21000 / 50000, 1)
        assert "치킨" in result["chicken_label"]
        assert "헬스장" in result["gym_label"]

    def test_0원(self):
        result = calc_spending_conversion(0)
        assert result["chicken"] == 0.0
        assert result["gym_months"] == 0.0

    def test_음수_입력(self):
        """음수는 0으로 클램핑."""
        result = calc_spending_conversion(-5000)
        assert result["chicken"] == 0.0
        assert result["gym_months"] == 0.0

    def test_매우_큰_값(self):
        result = calc_spending_conversion(10_000_000)
        assert result["chicken"] == round(10_000_000 / 20000, 1)
        assert isinstance(result["chicken_label"], str)

    def test_치킨_1마리_딱_맞는_금액(self):
        result = calc_spending_conversion(20000)
        assert result["chicken"] == 1.0


class TestCalcCalorieConversion:
    """calc_calorie_conversion 경계값 테스트."""

    def test_정상값(self):
        result = calc_calorie_conversion(1940)
        # RUNNING_KCAL_PER_MIN=10 → 1940/10=194.0
        assert result["running_min"] == round(1940 / 10, 1)
        assert result["walking_hours"] == round(1940 / 250, 1)
        assert "러닝" in result["running_label"]
        assert "걷기" in result["walking_label"]

    def test_0kcal(self):
        result = calc_calorie_conversion(0)
        assert result["running_min"] == 0.0
        assert result["walking_hours"] == 0.0

    def test_음수_입력(self):
        """음수는 0으로 클램핑."""
        result = calc_calorie_conversion(-100)
        assert result["running_min"] == 0.0
        assert result["walking_hours"] == 0.0

    def test_매우_큰_칼로리(self):
        result = calc_calorie_conversion(100_000)
        assert result["running_min"] == round(100_000 / 10, 1)
        assert isinstance(result["running_label"], str)

    def test_러닝_10분_딱_맞는_칼로리(self):
        result = calc_calorie_conversion(100)
        assert result["running_min"] == 10.0


# ── analyze() 통합 테스트 (FR-2~8) ──────────────────────

def test_csrf_토큰_없으면_403(logged_in_client):
    """CSRF 토큰 미포함 POST → 403."""
    res = logged_in_client.post(
        "/delivery/analyze",
        data={"image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 403


def test_업로드_5MB_초과시_413_핸들러_리다이렉트(logged_in_client):
    """MAX_CONTENT_LENGTH(5MB) 초과 업로드 → 413 핸들러가 flash + /delivery 리다이렉트. (#43)"""
    oversized = io.BytesIO(b"\x00" * (5 * 1024 * 1024 + 1))  # 5MB + 1byte
    res = logged_in_client.post(
        "/delivery/analyze",
        data={
            "csrf_token": "test-csrf-token",
            "image": (oversized, "big.png", "image/png"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 302
    assert "/delivery" in res.headers["Location"]


def test_영수증_분석_성공(logged_in_client):
    """FR-2~6: OCR → 칼로리 → 환산 → 코멘트 → 저장 → result.html 렌더링."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png"),
    }

    with (
        patch("routes.delivery.ai_ocr.parse_receipt", return_value=_OCR_OK),
        patch("routes.delivery.ai_calorie.estimate", return_value=_CAL_OK),
        patch("routes.delivery.ai_comment.generate", return_value=_COMMENT_OK),
        patch("routes.delivery.db", _make_db_mock()),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=data,
            content_type="multipart/form-data",
        )

    assert res.status_code == 200
    body = res.data.decode("utf-8")
    assert "후라이드치킨" in body
    assert "치킨" in body        # 환산 레이블
    assert "러닝" in body         # 칼로리 환산
    assert _COMMENT_OK in body


def test_ocr_실패시_수동입력_폼(logged_in_client):
    """FR-7: OCR 예외 발생 → /delivery/manual 리다이렉트."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png"),
    }

    with patch("routes.delivery.ai_ocr.parse_receipt", side_effect=Exception("OCR 오류")):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=data,
            content_type="multipart/form-data",
        )

    assert res.status_code == 302
    assert "/delivery/manual" in res.headers.get("Location", "")


def test_이미지_없이_분석_요청(logged_in_client):
    """FR-1: 이미지 없이 POST → /delivery 리다이렉트."""
    res = logged_in_client.post(
        "/delivery/analyze",
        data={"csrf_token": "test-csrf-token"},
        content_type="multipart/form-data",
    )
    assert res.status_code == 302
    assert "/delivery" in res.headers.get("Location", "")


def test_잘못된_파일형식(logged_in_client):
    """FR-1: PNG/JPG 외 파일 → /delivery 리다이렉트."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(b"fake gif data"), "receipt.gif", "image/gif"),
    }
    res = logged_in_client.post(
        "/delivery/analyze",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 302
    assert "/delivery" in res.headers.get("Location", "")


def test_가짜_png_파일형식(logged_in_client):
    """FR-1: image/png 선언이지만 매직 바이트가 없는 파일 → /delivery 리다이렉트 (MIME 스푸핑 차단)."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(b"this is not a real png"), "evil.png", "image/png"),
    }
    res = logged_in_client.post(
        "/delivery/analyze",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 302
    assert "/delivery" in res.headers.get("Location", "")


def test_칼로리_추론_실패시_부분_결과_진행(logged_in_client):
    """칼로리 실패 시에도 result.html을 렌더링한다 (부분 결과 허용)."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png"),
    }

    with (
        patch("routes.delivery.ai_ocr.parse_receipt", return_value=_OCR_OK),
        patch("routes.delivery.ai_calorie.estimate", side_effect=Exception("LLM 오류")),
        patch("routes.delivery.ai_comment.generate", return_value=_COMMENT_OK),
        patch("routes.delivery.db", _make_db_mock()),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=data,
            content_type="multipart/form-data",
        )

    assert res.status_code == 200


def test_코멘트_생성_실패시_부분_결과_진행(logged_in_client):
    """코멘트 실패 시에도 result.html을 렌더링한다 (부분 결과 허용)."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png"),
    }

    with (
        patch("routes.delivery.ai_ocr.parse_receipt", return_value=_OCR_OK),
        patch("routes.delivery.ai_calorie.estimate", return_value=_CAL_OK),
        patch("routes.delivery.ai_comment.generate", side_effect=Exception("LLM 오류")),
        patch("routes.delivery.db", _make_db_mock()),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=data,
            content_type="multipart/form-data",
        )

    assert res.status_code == 200


def test_db_저장_실패시_에러_리다이렉트(logged_in_client):
    """DB INSERT 실패 → /delivery 리다이렉트."""
    data = {
        "csrf_token": "test-csrf-token",
        "image": (io.BytesIO(_png_bytes()), "receipt.png", "image/png"),
    }

    @contextmanager
    def raising_db():
        raise Exception("DB 연결 실패")
        yield  # noqa: unreachable

    with (
        patch("routes.delivery.ai_ocr.parse_receipt", return_value=_OCR_OK),
        patch("routes.delivery.ai_calorie.estimate", return_value=_CAL_OK),
        patch("routes.delivery.ai_comment.generate", return_value=_COMMENT_OK),
        patch("routes.delivery.db", raising_db),
    ):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=data,
            content_type="multipart/form-data",
        )

    assert res.status_code == 302
    assert "/delivery" in res.headers.get("Location", "")


# ── 수동 입력 통합 테스트 (FR-7) ─────────────────────────

def test_수동_입력_분석_성공(logged_in_client):
    """FR-7: 수동 입력 폼 제출 → result.html 렌더링."""
    form_data = {
        "csrf_token": "test-csrf-token",
        "manual_input": "1",
        "food_names": "후라이드치킨, 콜라",
        "total_price": "21000",
        "delivery_fee": "3000",
    }

    with (
        patch("routes.delivery.ai_calorie.estimate", return_value=_CAL_OK),
        patch("routes.delivery.ai_comment.generate", return_value=_COMMENT_OK),
        patch("routes.delivery.db", _make_db_mock()),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        res = logged_in_client.post(
            "/delivery/analyze",
            data=form_data,
            content_type="application/x-www-form-urlencoded",
        )

    assert res.status_code == 200
    body = res.data.decode("utf-8")
    assert "치킨" in body
    assert _COMMENT_OK in body


def test_user_id_없으면_401(app):
    """user_id=None 시 abort(401) — defense-in-depth (login_required 우회 방어)."""
    with app.test_request_context(
        "/delivery/analyze",
        method="POST",
        data={"manual_input": "1", "food_names": "치킨", "total_price": "20000", "delivery_fee": "3000"},
        content_type="application/x-www-form-urlencoded",
    ):
        with pytest.raises(HTTPException) as exc_info:
            _handle_manual_input(None)
        assert exc_info.value.code == 401


def test_수동_입력_빈_음식명_거부(logged_in_client):
    """수동 입력 시 음식명이 없으면 flash error 후 /delivery/manual 로 리다이렉트."""
    form_data = {
        "csrf_token": "test-csrf-token",
        "manual_input": "1",
        "food_names": "",
        "total_price": "5000",
        "delivery_fee": "0",
    }

    res = logged_in_client.post(
        "/delivery/analyze",
        data=form_data,
        content_type="application/x-www-form-urlencoded",
    )

    assert res.status_code == 302
    assert "/delivery/manual" in res.headers.get("Location", "")


def test_수동_입력_음수_금액_거부(logged_in_client):
    """total_price 음수 제출 → flash error 후 /delivery/manual 리다이렉트."""
    form_data = {
        "csrf_token": "test-csrf-token",
        "manual_input": "1",
        "food_names": "후라이드치킨",
        "total_price": "-1000",
        "delivery_fee": "0",
    }

    res = logged_in_client.post(
        "/delivery/analyze",
        data=form_data,
        content_type="application/x-www-form-urlencoded",
    )

    assert res.status_code == 302
    assert "/delivery/manual" in res.headers.get("Location", "")


def test_수동_입력_비정수_금액_거부(logged_in_client):
    """total_price 비정수("abc") 제출 → flash error 후 /delivery/manual 리다이렉트."""
    form_data = {
        "csrf_token": "test-csrf-token",
        "manual_input": "1",
        "food_names": "후라이드치킨",
        "total_price": "abc",
        "delivery_fee": "0",
    }

    res = logged_in_client.post(
        "/delivery/analyze",
        data=form_data,
        content_type="application/x-www-form-urlencoded",
    )

    assert res.status_code == 302
    assert "/delivery/manual" in res.headers.get("Location", "")
