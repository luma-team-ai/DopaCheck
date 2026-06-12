"""챌린지 테스트 (담당: 오영석)."""
import pytest
from unittest.mock import MagicMock, patch


def _make_supabase_mock(data=None, count=0):
    """Supabase 체이닝 mock — 모든 메서드가 같은 mock_table을 반환한다."""
    mock_result = MagicMock()
    mock_result.data = data if data is not None else []
    mock_result.count = count

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = mock_result

    mock_sb = MagicMock()
    mock_sb.table.return_value = mock_table
    return mock_sb


def test_챌린지_페이지_렌더링(logged_in_client):
    """FR-32: 챌린지 목록 페이지가 200으로 응답한다."""
    with patch("routes.challenge.get_supabase", return_value=_make_supabase_mock()):
        res = logged_in_client.get("/challenge")
    assert res.status_code == 200


def test_챌린지_중복참여_차단(logged_in_client):
    """FR-35: 이미 참여 중인 챌린지에 재참여 시 409 반환."""
    challenge_id = "aaaaaaaa-0000-0000-0000-000000000001"
    mock_sb = _make_supabase_mock(data=[{"id": "existing-uc"}])

    with patch("routes.challenge.get_supabase", return_value=mock_sb):
        res = logged_in_client.post(f"/challenge/{challenge_id}/join")

    assert res.status_code == 409
    assert "이미 참여" in res.get_json()["error"]


@pytest.mark.skip(reason="TODO(오영석·김승현): recalculate_score 구현 후 달성 판정 통합 테스트 작성")
def test_챌린지_달성시_보너스_반영():
    """FR-37, FR-38: 달성 시 +5점"""
    ...
