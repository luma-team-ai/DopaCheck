"""마이페이지 테스트 — 기본 시급 설정(FR) + P2 보완(CSRF·상한 검증)."""
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

SESSION_USER_ID = 1
_CSRF_HEADERS = {"X-CSRF-Token": "test-csrf-token"}


def _patch_db(cursor):
    @contextmanager
    def fake_db():
        yield cursor

    return patch("routes.mypage.db", fake_db)


def _make_cursor(fetchone_side_effect=None):
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_side_effect
    return cursor


def test_마이페이지_렌더링(logged_in_client):
    """마이페이지가 200으로 응답하고 csrf_token이 포함된다."""
    fetchone_results = [
        {"nickname": "테스트", "email": "test@example.com", "created_at": datetime(2026, 1, 1), "hourly_wage": 10030},
        {"score": 80},
        {"cnt": 2},
        {"cnt": 1},
        {"cnt": 0},
    ]
    cursor = _make_cursor(fetchone_side_effect=fetchone_results)
    with _patch_db(cursor):
        res = logged_in_client.get("/mypage")
    assert res.status_code == 200
    assert b"csrf_token" in res.data


def test_시급_변경_성공(logged_in_client):
    """정상 범위의 시급은 200/리다이렉트로 반영된다."""
    cursor = _make_cursor()
    with _patch_db(cursor):
        res = logged_in_client.post(
            "/mypage/update_wage",
            data={"hourly_wage": "12000", "csrf_token": "test-csrf-token"},
        )
    assert res.status_code == 302
    cursor.execute.assert_called_once()


def test_시급_변경_csrf_미전송_403(logged_in_client):
    """CSRF 토큰 없는 요청은 403으로 차단된다."""
    cursor = _make_cursor()
    with _patch_db(cursor):
        res = logged_in_client.post("/mypage/update_wage", data={"hourly_wage": "12000"})
    assert res.status_code == 403


def test_시급_변경_상한_초과_거부(logged_in_client):
    """P2: 상한(1,000,000원)을 초과하는 시급은 거부되고 UPDATE가 실행되지 않는다."""
    cursor = _make_cursor()
    with _patch_db(cursor):
        res = logged_in_client.post(
            "/mypage/update_wage",
            data={"hourly_wage": "1000001", "csrf_token": "test-csrf-token"},
        )
    assert res.status_code == 302
    cursor.execute.assert_not_called()


def test_시급_변경_음수_거부(logged_in_client):
    """음수 시급은 거부되고 UPDATE가 실행되지 않는다."""
    cursor = _make_cursor()
    with _patch_db(cursor):
        res = logged_in_client.post(
            "/mypage/update_wage",
            data={"hourly_wage": "-1", "csrf_token": "test-csrf-token"},
        )
    assert res.status_code == 302
    cursor.execute.assert_not_called()
