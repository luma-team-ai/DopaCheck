"""시간 분석 테스트 (담당: 이은석)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from config import BOOK_HOURS, DEFAULT_HOURLY_WAGE, LECTURE_HOURS, WORKOUT_HOURS


_WEEK_ROW = {"yt": 0, "ig": 0, "tt": 0, "gm": 0}  # 이번 주 누적 mock 기본값


@contextmanager
def _fake_db():
    """time_page 본문 쿼리에 맞춘 커서 mock.

    fetchone 호출 순서:
    1. users SELECT hourly_wage       → {"hourly_wage": ...}
    2. _get_week_totals SUM 집계 쿼리 → _WEEK_ROW
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"hourly_wage": DEFAULT_HOURLY_WAGE},
        _WEEK_ROW,
    ]
    yield cursor


@contextmanager
def _fake_db_analyze():
    """analyze 본문 쿼리(INSERT + UPDATE + _get_week_totals) mock.

    fetchone 호출 순서:
    1. _get_week_totals SUM 집계 쿼리 → _WEEK_ROW
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [_WEEK_ROW]
    yield cursor


def test_입력_폼_렌더링(logged_in_client):
    # 입력 폼 라우트는 users.hourly_wage 단일 조회만 수행하므로 db만 mock.
    with patch("routes.time.db", _fake_db):
        assert logged_in_client.get("/time").status_code == 200


def test_시간_분석_성공(logged_in_client):
    """FR-11~15: 정상 입력 + CSRF 토큰 동봉 → 200, AI 코멘트 포함."""
    with (
        patch("routes.time.db", _fake_db_analyze),
        patch("routes.time.ai_comment.generate", return_value="잘하셨어요!"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "2.0",
                "instagram_h": "1.0",
                "tiktok_h":    "0.5",
                "game_h":      "1.5",
                "hourly_wage": "10000",
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200
    assert "잘하셨어요!" in resp.data.decode()


def test_시간_환산_경계값(logged_in_client):
    """FR-11, FR-12 + PRD §9 경계값: 0시간·음수·168h 초과 입력."""
    # ── 0시간 입력: 책·강의·운동 환산 모두 0.0 ──────────────────────
    with (
        patch("routes.time.db", _fake_db_analyze),
        patch("routes.time.ai_comment.generate", return_value="0시간 테스트"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "0",
                "instagram_h": "0",
                "tiktok_h":    "0",
                "game_h":      "0",
                "hourly_wage": str(DEFAULT_HOURLY_WAGE),
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200
    body = resp.data.decode()
    # sns_total=0 → book_n=0.0, lecture_n=0.0, workout_n=0.0
    assert str(round(0 / BOOK_HOURS, 1)) in body       # "0.0"
    assert str(round(0 / LECTURE_HOURS, 1)) in body    # "0.0"
    assert str(round(0 / WORKOUT_HOURS, 1)) in body    # "0.0"

    # ── 음수 입력: 클램핑되어 0.0 처리 ──────────────────────────────
    with (
        patch("routes.time.db", _fake_db_analyze),
        patch("routes.time.ai_comment.generate", return_value="음수 테스트"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "-5",
                "instagram_h": "-10",
                "tiktok_h":    "0",
                "game_h":      "0",
                "hourly_wage": str(DEFAULT_HOURLY_WAGE),
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200

    # ── 24h 초과 입력: 각 필드 24h로 클램핑 ────────────────────────
    with (
        patch("routes.time.db", _fake_db_analyze),
        patch("routes.time.ai_comment.generate", return_value="초과 테스트"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "999",   # max(0, min(999, 24)) = 24
                "instagram_h": "0",
                "tiktok_h":    "0",
                "game_h":      "0",
                "hourly_wage": str(DEFAULT_HOURLY_WAGE),
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200


def test_주간_누적_분에서_시간_환산(logged_in_client):
    """P2-2: week row(분 단위)가 시간 단위로 올바르게 환산되어 렌더되는지 검증.

    youtube 90분→1.5h, game 1200분→20.0h, instagram/tiktok 0 →
    week_total_h = 21.5h. _fake_db_analyze와 동일한 fetchone 순서
    (analyze는 INSERT+UPDATE 후 _get_week_totals SUM 집계 1회)를 따른다.
    """
    week_row = {"yt": 90, "ig": 0, "tt": 0, "gm": 1200}

    @contextmanager
    def _fake_db_week():
        cursor = MagicMock()
        cursor.fetchone.side_effect = [week_row]
        yield cursor

    with (
        patch("routes.time.db", _fake_db_week),
        patch("routes.time.ai_comment.generate", return_value="환산 테스트"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "0",
                "instagram_h": "0",
                "tiktok_h":    "0",
                "game_h":      "0",
                "hourly_wage": str(DEFAULT_HOURLY_WAGE),
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200
    body = resp.data.decode()
    # 90분 → 1.5h, 1200분 → 20.0h, 합계 21.5h
    assert "1.5" in body   # week_youtube_h
    assert "20.0" in body  # week_game_h
    assert "21.5" in body  # week_total_h


def test_analyze_CSRF_없으면_403(logged_in_client):
    """CSRF 토큰 미전송 시 /time/analyze → 403.

    verify_csrf()가 abort(403)을 발생시키므로 DB·AI 호출 이전에 차단된다.
    """
    resp = logged_in_client.post(
        "/time/analyze",
        data={
            "youtube_h":   "1.0",
            "instagram_h": "1.0",
            "tiktok_h":    "0.0",
            "game_h":      "0.0",
            "hourly_wage": "10000",
            # csrf_token 의도적 누락
        },
    )
    assert resp.status_code == 403


def test_analyze_잘못된_CSRF_토큰_403(logged_in_client):
    """틀린 CSRF 토큰 전송 시 /time/analyze → 403 (타이밍 공격 방어 포함)."""
    resp = logged_in_client.post(
        "/time/analyze",
        data={
            "youtube_h":   "1.0",
            "instagram_h": "0.0",
            "tiktok_h":    "0.0",
            "game_h":      "0.0",
            "hourly_wage": "10000",
            "csrf_token":  "wrong-token",
        },
    )
    assert resp.status_code == 403


def test_analyze_정상_CSRF_토큰_통과(logged_in_client):
    """올바른 CSRF 토큰 동봉 시 /time/analyze → 403이 아닌 200 (대조 케이스).

    conftest.logged_in_client가 세션에 주입한 'test-csrf-token'을 그대로 전송.
    """
    with (
        patch("routes.time.db", _fake_db_analyze),
        patch("routes.time.ai_comment.generate", return_value="대조 테스트"),
        patch("services.score_service.recalculate_score", side_effect=NotImplementedError),
    ):
        resp = logged_in_client.post(
            "/time/analyze",
            data={
                "youtube_h":   "2.0",
                "instagram_h": "1.0",
                "tiktok_h":    "0.0",
                "game_h":      "0.5",
                "hourly_wage": "10000",
                "csrf_token":  "test-csrf-token",
            },
        )
    assert resp.status_code == 200
