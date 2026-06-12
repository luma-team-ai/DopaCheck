"""히스토리 테스트 (담당: 허남)."""
import pytest


def test_히스토리_목록_렌더링(logged_in_client):
    assert logged_in_client.get("/history").status_code == 200


@pytest.mark.skip(reason="TODO(허남): 조회/삭제 구현 후 작성")
def test_기간_필터():
    """FR-24: week / month / all"""
    ...


@pytest.mark.skip(reason="TODO(허남): 삭제 구현 후 작성 — 타인 기록 삭제 차단 포함")
def test_기록_삭제():
    """FR-23"""
    ...
