"""챌린지 테스트 (담당: 오영석)."""
import pytest


def test_챌린지_페이지_렌더링(logged_in_client):
    assert logged_in_client.get("/challenge").status_code == 200


@pytest.mark.skip(reason="TODO(오영석): 참여 로직 구현 후 작성")
def test_챌린지_중복참여_차단():
    """FR-35"""
    ...


@pytest.mark.skip(reason="TODO(오영석·김승현): 달성 판정 트리거 구현 후 작성")
def test_챌린지_달성시_보너스_반영():
    """FR-37, FR-38: 달성 시 +5점"""
    ...
