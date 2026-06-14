"""홈 대시보드 라우트 테스트."""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@contextmanager
def _fake_db():
    """home.index 본문 쿼리에 맞춘 커서 mock.

    PR50 home.py의 fetchone 호출 순서:
    1. dopamine_scores SELECT (이번 주 점수/기여도)
    2. COUNT(*) 전체 유저 수 → {"cnt": ...}
    3. COUNT(*) 나보다 높은 유저 수 → {"cnt": ...}
    4. AVG(score) 전체 평균 → {"avg_score": ...}
    5. SUM(total_price) 배달 총액 → {"sum_price": ...}
    6. SUM(...분) 사용 시간 → {"sum_min": ...}
    7. COUNT(*) 참여 챌린지 수 → {"total_cnt": ...}
    8. COUNT(*) 완료 챌린지 수 → {"comp_cnt": ...}
    9. dopamine_scores SELECT (지난주 점수)
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
        {"cnt": 20},        # 전체 유저 수
        {"cnt": 5},         # 나보다 점수 높은 유저 수
        {"avg_score": 65.0},  # 전체 평균 점수
        {"sum_price": 30000},  # 배달 총액
        {"sum_min": 150},      # 사용 시간(분)
        {"total_cnt": 3},      # 참여 챌린지 수
        {"comp_cnt": 1},       # 완료 챌린지 수
        {"score": 65},         # 지난주 점수
    ]
    yield cursor


def test_비로그인_홈_접속_시_로그인_페이지_리다이렉트(client):
    """로그인 안 한 유저는 로그인 페이지로 리다이렉트되어야 한다."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_로그인_홈_페이지_렌더링(logged_in_client):
    """로그인 한 유저는 홈 대시보드가 정상적으로 렌더링(200 OK)되어야 한다."""
    # recalculate_score는 별도 DB 접속을 일으키므로 no-op 처리하고,
    # 페이지 본문 쿼리만 _fake_db로 mock한다.
    with patch("services.score_service.recalculate_score", lambda user_id: None), \
            patch("routes.home.db", _fake_db):
        response = logged_in_client.get("/", follow_redirects=True)
    assert response.status_code == 200
    html_content = response.data.decode("utf-8")
    assert "DopaCheck" in html_content
    assert "이번 주 도파민 점수" in html_content
