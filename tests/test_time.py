"""시간 분석 테스트 (담당: 이은석)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from config import DEFAULT_HOURLY_WAGE


@contextmanager
def _fake_db():
    """time_page 본문 쿼리에 맞춘 커서 mock.

    PR52 time.py의 time_page fetchone 호출:
    1. users SELECT hourly_wage → {"hourly_wage": ...}
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"hourly_wage": DEFAULT_HOURLY_WAGE},  # 테스트 픽스처값(= config.DEFAULT_HOURLY_WAGE)
    ]
    yield cursor


def test_입력_폼_렌더링(logged_in_client):
    # 입력 폼 라우트는 users.hourly_wage 단일 조회만 수행하므로 db만 mock.
    with patch("routes.time.db", _fake_db):
        assert logged_in_client.get("/time").status_code == 200


@pytest.mark.skip(reason="TODO(이은석): 분석 파이프라인 구현 후 작성")
def test_시간_분석_성공():
    """FR-11~15: 환산 → 코멘트 → 차트 → 저장."""
    ...


@pytest.mark.skip(reason="TODO(이은석): 환산 로직 구현 후 작성 — 경계값(0, 음수, 매우 큰 값) 포함")
def test_시간_환산_경계값():
    """FR-11, FR-12 + PRD §9 경계값 테스트"""
    ...
