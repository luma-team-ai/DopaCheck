"""AI 모듈 테스트 (담당: 오영석)."""
import pytest


@pytest.mark.skip(reason="TODO(오영석): OCR 구현 후 작성 — 샘플 영수증 5종, 추출 성공률 80% 목표 (PRD §9)")
def test_ocr_샘플_영수증_파싱():
    """FR-40"""
    ...


@pytest.mark.skip(reason="TODO(오영석): 칼로리 추론 구현 후 작성")
def test_칼로리_추론():
    """FR-41"""
    ...


@pytest.mark.skip(reason="TODO(오영석): 코멘트 생성 구현 후 작성 — type별(delivery/time/report) 분기")
def test_공감_코멘트_생성():
    """FR-42"""
    ...
