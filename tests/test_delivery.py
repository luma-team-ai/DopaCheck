"""배달 분석 테스트 (담당: 김관영)."""
import pytest


def test_업로드_폼_렌더링(logged_in_client):
    assert logged_in_client.get("/delivery").status_code == 200


@pytest.mark.skip(reason="TODO(김관영): 분석 파이프라인 구현 후 작성")
def test_영수증_분석_성공():
    """FR-2~6: OCR → 칼로리 → 환산 → 코멘트 → 저장."""
    ...


@pytest.mark.skip(reason="TODO(김관영): OCR 실패 fallback 구현 후 작성")
def test_ocr_실패시_수동입력_폼():
    """FR-7"""
    ...


@pytest.mark.skip(reason="TODO(김관영): 환산 로직 구현 후 작성 — 경계값(0, 음수, 매우 큰 값) 포함")
def test_지출_칼로리_환산_경계값():
    """FR-4, FR-5 + PRD §9 경계값 테스트"""
    ...
