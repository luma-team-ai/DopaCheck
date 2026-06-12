"""도파민 점수 테스트 (담당: 김승현)."""
import pytest


def test_점수_페이지_렌더링(logged_in_client):
    assert logged_in_client.get("/score").status_code == 200


@pytest.mark.skip(reason="TODO(김승현·오영석): ai.score.calculate 구현 후 작성")
def test_점수_산출_입출력():
    """FR-26, FR-27: 0~100 범위, 가중치 40/40/20 검증 (PRD §9)"""
    ...


@pytest.mark.skip(reason="TODO(김승현): recalculate_score 구현 후 작성")
def test_분석_저장시_점수_재산출():
    """FR-31: upsert 동작 검증"""
    ...
