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


@pytest.mark.skip(reason="TODO(오영석·김승현): recalculate_score 구현 후 달성 판정 통합 테스트 작성")
def test_챌린지_달성시_보너스_반영():
    """FR-37, FR-38: 달성 시 +5점"""
    ...
