"""종합 리포트 테스트 (담당: 정재봉)."""
from __future__ import annotations

import pytest
from unittest.mock import patch


# ── 페이지 렌더링 ────────────────────────────────────────────────────────────

def test_리포트_페이지_렌더링(logged_in_client):
    """로그인 상태에서 /report가 200을 반환해야 한다 (FR-16)."""
    assert logged_in_client.get("/report").status_code == 200


def test_비로그인_리포트_접근_리다이렉트(client):
    """비로그인 상태에서 /report는 /login으로 리다이렉트해야 한다 (FR-0)."""
    res = client.get("/report")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


# ── aggregate_delivery 순수 함수 경계값 테스트 ──────────────────────────────

from routes.report import aggregate_delivery


def test_aggregate_delivery_빈_리스트():
    result = aggregate_delivery([])
    assert result == {"total_price": 0, "total_calories": 0, "count": 0}


def test_aggregate_delivery_단일_행():
    rows = [{"total_price": 25000, "total_calories": 1200}]
    result = aggregate_delivery(rows)
    assert result["total_price"] == 25000
    assert result["total_calories"] == 1200
    assert result["count"] == 1


def test_aggregate_delivery_복수_행_합산():
    rows = [
        {"total_price": 15000, "total_calories": 800},
        {"total_price": 20000, "total_calories": 1500},
        {"total_price": 35000, "total_calories": 2000},
    ]
    result = aggregate_delivery(rows)
    assert result["total_price"] == 70000
    assert result["total_calories"] == 4300
    assert result["count"] == 3


def test_aggregate_delivery_None_값_처리():
    """total_calories가 None인 행이 있어도 0으로 처리해야 한다."""
    rows = [
        {"total_price": 18000, "total_calories": None},
        {"total_price": 12000, "total_calories": 900},
    ]
    result = aggregate_delivery(rows)
    assert result["total_price"] == 30000
    assert result["total_calories"] == 900


def test_aggregate_delivery_큰_값():
    rows = [{"total_price": 10_000_000, "total_calories": 999_999}]
    result = aggregate_delivery(rows)
    assert result["total_price"] == 10_000_000
    assert result["total_calories"] == 999_999


# ── aggregate_time 순수 함수 경계값 테스트 ──────────────────────────────────

from routes.report import aggregate_time


def test_aggregate_time_빈_리스트():
    result = aggregate_time([])
    assert result == {
        "youtube_min": 0,
        "instagram_min": 0,
        "tiktok_min": 0,
        "game_min": 0,
        "total_min": 0,
    }


def test_aggregate_time_단일_행():
    rows = [{"youtube_min": 60, "instagram_min": 30, "tiktok_min": 0, "game_min": 120}]
    result = aggregate_time(rows)
    assert result["youtube_min"] == 60
    assert result["instagram_min"] == 30
    assert result["tiktok_min"] == 0
    assert result["game_min"] == 120
    assert result["total_min"] == 210


def test_aggregate_time_복수_행_합산():
    rows = [
        {"youtube_min": 60, "instagram_min": 30, "tiktok_min": 20, "game_min": 0},
        {"youtube_min": 90, "instagram_min": 0, "tiktok_min": 10, "game_min": 60},
    ]
    result = aggregate_time(rows)
    assert result["youtube_min"] == 150
    assert result["instagram_min"] == 30
    assert result["tiktok_min"] == 30
    assert result["game_min"] == 60
    assert result["total_min"] == 270


def test_aggregate_time_None_값_처리():
    rows = [{"youtube_min": None, "instagram_min": 45, "tiktok_min": None, "game_min": 0}]
    result = aggregate_time(rows)
    assert result["youtube_min"] == 0
    assert result["instagram_min"] == 45
    assert result["total_min"] == 45


def test_aggregate_time_큰_값():
    rows = [{"youtube_min": 10000, "instagram_min": 5000, "tiktok_min": 3000, "game_min": 2000}]
    result = aggregate_time(rows)
    assert result["total_min"] == 20000


# ── get_week_ranges 주차 계산 테스트 ────────────────────────────────────────

from datetime import date
from utils.week import get_week_ranges, week_bounds


def test_week_bounds_월요일():
    monday = date(2026, 6, 8)  # 월요일
    start, end = week_bounds(monday)
    assert start == "2026-06-08"
    assert end == "2026-06-14"


def test_week_bounds_일요일():
    sunday = date(2026, 6, 14)  # 일요일
    start, end = week_bounds(sunday)
    assert start == "2026-06-08"
    assert end == "2026-06-14"


def test_week_bounds_수요일():
    wednesday = date(2026, 6, 10)
    start, end = week_bounds(wednesday)
    assert start == "2026-06-08"
    assert end == "2026-06-14"


def test_get_week_ranges_이번주_저번주_차이():
    """이번 주 시작일은 저번 주 시작일보다 7일 뒤여야 한다."""
    from datetime import date as dt_date
    this, last = get_week_ranges()
    this_start = dt_date.fromisoformat(this[0])
    last_start = dt_date.fromisoformat(last[0])
    assert (this_start - last_start).days == 7


# ── AI fallback 테스트 (FR-45) ───────────────────────────────────────────────

def test_AI_fallback_페이지_200(logged_in_client):
    """ai.comment.generate가 NotImplementedError를 던져도 /report가 200을 반환해야 한다."""
    # ai.comment.generate는 현재 NotImplementedError 상태이므로 별도 monkeypatch 없이도 통과
    res = logged_in_client.get("/report")
    assert res.status_code == 200


def test_AI_예외_발생해도_페이지_200(logged_in_client):
    """ai.comment.generate가 RuntimeError 등 일반 예외를 던져도 200이어야 한다."""
    with patch("ai.comment.generate", side_effect=RuntimeError("API 오류")):
        res = logged_in_client.get("/report")
    assert res.status_code == 200


def test_AI_정상_작동시_코멘트_반영(logged_in_client):
    """ai.comment.generate가 정상 반환하면 그 문자열이 응답에 포함되어야 한다."""
    fake_comment = "이번 주도 수고했어요! 다음 주엔 조금 줄여봐요."
    with patch("ai.comment.generate", return_value=fake_comment):
        res = logged_in_client.get("/report")
    assert res.status_code == 200
    assert fake_comment.encode() in res.data


# ── 주간 집계 및 비교 차트 데이터 통합 테스트 (FR-16, FR-20) ────────────────

def test_주간_집계_및_비교차트_데이터(logged_in_client):
    """DB 없이 빈 데이터 폴백으로 /report가 정상 렌더링되어야 한다 (FR-16, FR-20)."""
    res = logged_in_client.get("/report")
    assert res.status_code == 200
    # 비교 차트 Canvas가 렌더링되어야 함 (#142 재디자인: 단일 compareChart → 배달·시간·점수 3분할)
    assert b"chartDelivery" in res.data
    assert b"chartTime" in res.data
    assert b"chartScore" in res.data
    # 공유 카드 영역이 존재해야 함
    assert b'id="share-card"' in res.data


# ── _fetch_score challenge_bonus 음수 보존 테스트 (#175 P1-A) ────────────────

from unittest.mock import MagicMock, patch
from routes.report import _fetch_score


def _make_db_mock(row: dict):
    """db() 컨텍스트 매니저를 row 하나 반환하도록 mock한다."""
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = row
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cursor_mock)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_fetch_score_challenge_bonus_음수_유지():
    """challenge_bonus=-10이 0으로 죽지 않고 -10으로 반환되어야 한다 (#175 P1-A)."""
    row = {"score": 55, "delivery_contribution": 40, "time_contribution": 15, "challenge_bonus": -10}
    with patch("routes.report.db", return_value=_make_db_mock(row)):
        result = _fetch_score(1, "2026-06-08")
    assert result["challenge_bonus"] == -10


def test_fetch_score_challenge_bonus_최솟값_클램프():
    """challenge_bonus가 -20 미만이면 -20으로 강제 클램프되어야 한다 (#175 P1-A)."""
    row = {"score": 80, "delivery_contribution": 50, "time_contribution": 30, "challenge_bonus": -25}
    with patch("routes.report.db", return_value=_make_db_mock(row)):
        result = _fetch_score(1, "2026-06-08")
    assert result["challenge_bonus"] == -20


def test_fetch_score_challenge_bonus_양수_입력_0으로_클램프():
    """challenge_bonus가 비정상 양수로 들어와도 0으로 클램프된다 (#175 P1-A)."""
    row = {"score": 30, "delivery_contribution": 20, "time_contribution": 10, "challenge_bonus": 5}
    with patch("routes.report.db", return_value=_make_db_mock(row)):
        result = _fetch_score(1, "2026-06-08")
    assert result["challenge_bonus"] == 0


def test_fetch_score_challenge_bonus_None_처리():
    """challenge_bonus가 None이면 0을 반환한다 (#175 P1-A)."""
    row = {"score": 45, "delivery_contribution": 30, "time_contribution": 15, "challenge_bonus": None}
    with patch("routes.report.db", return_value=_make_db_mock(row)):
        result = _fetch_score(1, "2026-06-08")
    assert result["challenge_bonus"] == 0


# ── clamp_score 경계값 테스트 (점수 0~100 강제 — conic-gradient 방어) ────────

from routes.report import clamp_score


def test_clamp_score_정상_범위():
    assert clamp_score(0) == 0
    assert clamp_score(72) == 72
    assert clamp_score(100) == 100


def test_clamp_score_범위_초과_및_음수():
    assert clamp_score(150) == 100   # 상한 강제
    assert clamp_score(-10) == 0     # 하한 강제


def test_clamp_score_None_및_비정상_입력():
    assert clamp_score(None) == 0
    assert clamp_score("bad") == 0


# ── report 진입 시 recalculate_score 호출 검증 (#75) ─────────────────────────

def test_report_진입_시_recalculate_score_호출됨(logged_in_client):
    """report 페이지 진입 시 recalculate_score가 정확히 1회 호출되어야 한다 (#75).

    home.py·score.py와 동일 패턴으로 이번 주 점수를 재산출한 뒤 조회해야
    진입 경로에 따른 점수 불일치(stale 0 문제)가 사라진다.
    """
    # patch 대상은 report 모듈에 바인딩된 이름(#83) — 모듈 최상위 import로 전환돼 리팩터링에도 안전.
    with patch("routes.report.recalculate_score") as mock_recalc:
        res = logged_in_client.get("/report")
    assert res.status_code == 200
    # logged_in_client는 user_id=1 주입(conftest) — 인자까지 검증해 호출 신뢰성 확보
    mock_recalc.assert_called_once_with(1)


def test_report_recalculate_score_예외_발생해도_200(logged_in_client):
    """recalculate_score가 예외를 던져도 report 페이지는 200을 반환해야 한다 (#75).

    예외는 logger.warning으로 삼키고, 폴백으로 기존 점수(또는 0)를 표시한다.
    """
    with patch("routes.report.recalculate_score", side_effect=RuntimeError("DB 오류")):
        res = logged_in_client.get("/report")
    assert res.status_code == 200


# ── kst_bounds 타임존·경계 테스트 (created_at 누락 방지) ────────────────────

from utils.week import kst_bounds


def test_kst_bounds_MariaDB_DATETIME_포맷():
    """경계 문자열은 MariaDB DATETIME 호환(KST-naive, 공백 구분, 오프셋 없음)이어야 한다.

    'T' 구분자나 +09:00 오프셋이 들어가면 MariaDB DATETIME 비교가 실패해
    해당 주 레코드가 조용히 0건으로 누락된다(#21 회귀 차단). DB 세션 TZ는 +09:00 고정.
    """
    gte_at, lt_at = kst_bounds("2026-06-08", "2026-06-14")
    assert gte_at == "2026-06-08 00:00:00"
    # 종료 경계는 일요일 익일(월요일) 00:00 미만 — 일요일 23:59:59.x 누락 방지
    assert lt_at == "2026-06-15 00:00:00"
    # MariaDB DATETIME 리터럴과 어긋나는 토큰이 없어야 한다.
    assert "T" not in gte_at and "+09:00" not in gte_at
    assert "T" not in lt_at and "+09:00" not in lt_at
