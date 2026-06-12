"""종합 리포트 테스트 (담당: 정재봉)."""
import pytest


def test_리포트_페이지_렌더링(logged_in_client):
    assert logged_in_client.get("/report").status_code == 200


@pytest.mark.skip(reason="TODO(정재봉): 대시보드 집계 구현 후 작성")
def test_주간_집계_및_비교차트_데이터():
    """FR-16, FR-20"""
    ...
