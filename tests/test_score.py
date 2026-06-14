import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@contextmanager
def _fake_db():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
        {"avg_score": 65.0},
        {"cnt": 3},
        {"cnt": 20},
    ]
    yield cursor


def test_점수_페이지_렌더링(logged_in_client):
    with patch("routes.score.db", _fake_db):
        assert logged_in_client.get("/score").status_code == 200


@pytest.mark.skip(reason="TODO(김승현·오영석): ai.score.calculate 구현 후 작성")
def test_점수_산출_입출력():
    """FR-26, FR-27: 0~100 범위, 가중치 40/40/20 검증 (PRD §9)"""
    ...


@pytest.mark.skip(reason="TODO(김승현): recalculate_score 구현 후 작성")
def test_분석_저장시_점수_재산출():
    """FR-31: upsert 동작 검증"""
    ...
