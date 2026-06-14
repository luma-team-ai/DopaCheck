import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@contextmanager
def _fake_db():
    """score_page 본문 쿼리에 맞춘 커서 mock.

    PR50 score.py의 fetchone 호출 순서:
    1. dopamine_scores SELECT (이번 주 점수/기여도)
    2. COUNT(*) 전체 유저 수 → {"cnt": ...}
    3. COUNT(*) 나보다 높은 유저 수 → {"cnt": ...}
    4. dopamine_scores SELECT (지난주 점수)
    5. AVG(...) 시간 통계 → {"avg_min": ...}
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
        {"cnt": 20},   # 전체 유저 수
        {"cnt": 5},    # 나보다 점수 높은 유저 수
        {"score": 65},  # 지난주 점수
        {"avg_min": 120},  # 이번 주 평균 사용 시간(분)
    ]
    yield cursor


def test_점수_페이지_렌더링(logged_in_client):
    # recalculate_score는 별도 DB 접속을 일으키므로 no-op 처리하고,
    # 페이지 본문 쿼리만 _fake_db로 mock한다.
    with patch("routes.score.recalculate_score", lambda user_id: None), \
            patch("routes.score.db", _fake_db):
        assert logged_in_client.get("/score").status_code == 200


@pytest.mark.skip(reason="TODO(김승현·오영석): ai.score.calculate 구현 후 작성")
def test_점수_산출_입출력():
    """FR-26, FR-27: 0~100 범위, 가중치 40/40/20 검증 (PRD §9)"""
    ...


@pytest.mark.skip(reason="TODO(김승현): recalculate_score 구현 후 작성")
def test_분석_저장시_점수_재산출():
    """FR-31: upsert 동작 검증"""
    ...
