"""챌린지 테스트 (담당: 오영석)."""
from contextlib import contextmanager

import pytest
from unittest.mock import MagicMock, patch


def _make_db_mock(fetchall=None, fetchone=None):
    """db() 컨텍스트매니저 mock — cursor.fetchall/fetchone 반환값 지정."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall if fetchall is not None else []
    mock_cursor.fetchone.return_value = fetchone

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


def test_챌린지_페이지_렌더링(logged_in_client):
    """FR-32: 챌린지 목록 페이지가 200으로 응답한다."""
    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.get("/challenge")
    assert res.status_code == 200


def test_챌린지_중복참여_차단(logged_in_client):
    """FR-35: 이미 참여 중인 챌린지에 재참여 시 409 반환."""
    challenge_id = "aaaaaaaa-0000-0000-0000-000000000001"

    with patch("routes.challenge.db", _make_db_mock(fetchone={"id": "existing-uc"})):
        res = logged_in_client.post(f"/challenge/{challenge_id}/join")

    assert res.status_code == 409
    assert "이미 참여" in res.get_json()["error"]


def test_top_app_전부_0이면_recommend_history에서_제외(logged_in_client):
    """app_totals 합계가 0이면 top_app/top_app_hours 없이 recommend 호출된다."""
    call_count = [0]

    @contextmanager
    def mock_db_seq():
        cursor = MagicMock()

        def fetchone_side():
            call_count[0] += 1
            # has_delivery=있음, has_time=없음(None)
            return {"id": "x"} if call_count[0] == 1 else None

        cursor.fetchone.side_effect = fetchone_side
        cursor.fetchall.side_effect = [
            # challenges 목록
            [],
            # user_challenges
            [],
            # delivery_rows
            [{"created_at": "2024-01-01"}],
            # time_rows — 전부 0
            [{"youtube_min": 0, "instagram_min": 0, "tiktok_min": 0, "game_min": 0}],
        ]
        yield cursor

    captured = {}

    def fake_recommend(history):
        captured["history"] = history
        return {"recommendations": []}

    with patch("routes.challenge.db", mock_db_seq), \
         patch("routes.challenge.ai_challenge.recommend", fake_recommend):
        res = logged_in_client.get("/challenge")

    assert res.status_code == 200
    assert "top_app" not in captured.get("history", {}), \
        "합계 0이면 top_app이 history에 포함되면 안 됨"


@pytest.mark.skip(reason="TODO(오영석·김승현): recalculate_score 구현 후 달성 판정 통합 테스트 작성")
def test_챌린지_달성시_보너스_반영():
    """FR-37, FR-38: 달성 시 +5점"""
    ...
