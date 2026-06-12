"""시간 분석 테스트 (담당: 이은석)."""
import pytest


def test_입력_폼_렌더링(logged_in_client):
    assert logged_in_client.get("/time").status_code == 200


@pytest.mark.skip(reason="TODO(이은석): 분석 파이프라인 구현 후 작성")
def test_시간_분석_성공():
    """FR-11~15: 환산 → 코멘트 → 차트 → 저장."""
    ...


@pytest.mark.skip(reason="TODO(이은석): 환산 로직 구현 후 작성 — 경계값(0, 음수, 매우 큰 값) 포함")
def test_시간_환산_경계값():
    """FR-11, FR-12 + PRD §9 경계값 테스트"""
    ...
