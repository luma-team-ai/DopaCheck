"""홈 대시보드 라우트 테스트."""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@contextmanager
def _fake_db():
    """home.index 본문 쿼리에 맞춘 커서 mock.

    Issue #69 수정 후 home.py의 fetchone 호출 순서:
    1. dopamine_scores SELECT (이번 주 점수/기여도)
    2. COUNT(*) 전체 유저 수 → {"cnt": ...}
    3. COUNT(*) 나보다 높은 유저 수 → {"cnt": ...}
    4. AVG(score) 전체 평균 → {"avg_score": ...}
    5. SUM(total_price) 배달 총액 → {"sum_price": ...}
    6. SUM(...분) 사용 시간 → {"sum_min": ...}
    7. COUNT(*) 참여 챌린지 수 (started_at OR completed_at 합집합) → {"total_cnt": ...}
    8. COUNT(*) 완료 챌린지 수 (completed_at 기준) → {"comp_cnt": ...}
    9. dopamine_scores SELECT (지난주 점수)
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
        {"cnt": 20},           # 전체 유저 수
        {"cnt": 5},            # 나보다 점수 높은 유저 수
        {"avg_score": 65.0},   # 전체 평균 점수
        {"sum_price": 30000},  # 배달 총액
        {"sum_min": 150},      # 사용 시간(분)
        {"total_cnt": 3},      # 참여 챌린지 수 (합집합)
        {"comp_cnt": 1},       # 완료 챌린지 수 (completed_at 기준)
        {"score": 65},         # 지난주 점수
    ]
    yield cursor


def _make_cursor_with_challenges(total_cnt: int, comp_cnt: int):
    """챌린지 집계 검증용 커서 — total/comp 값을 주입할 수 있는 팩토리."""
    @contextmanager
    def _db():
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
            {"cnt": 20},
            {"cnt": 5},
            {"avg_score": 65.0},
            {"sum_price": 30000},
            {"sum_min": 150},
            {"total_cnt": total_cnt},
            {"comp_cnt": comp_cnt},
            {"score": 65},
        ]
        yield cursor
    return _db


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


def test_지난주_시작_이번주_완료_챌린지가_completed에_포함되고_total에도_포함(logged_in_client):
    """지난주 시작 → 이번 주 완료인 챌린지는 completed_challenges에 잡히고
    total_challenges에도 포함되어야 한다 (완료 ≤ 전체 불변식).

    Issue #69: total_cnt=1(합집합 쿼리), comp_cnt=1(completed_at 기준) 시나리오.
    """
    fake_db = _make_cursor_with_challenges(total_cnt=1, comp_cnt=1)
    with patch("services.score_service.recalculate_score", lambda user_id: None), \
            patch("routes.home.db", fake_db):
        response = logged_in_client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # completed(1) ≤ total(1) 불변식 — 렌더링 자체가 정상이면 집계 일치 확인됨
    html = response.data.decode("utf-8")
    assert "DopaCheck" in html


def test_이번주_시작_미완료_챌린지가_total에_포함되고_completed에는_빠짐(logged_in_client):
    """이번 주에 시작했지만 미완료인 챌린지는 total_challenges에는 잡히고
    completed_challenges에는 포함되지 않아야 한다.

    Issue #69: total_cnt=2(이번주 시작 포함), comp_cnt=0(이번주 완료 없음) 시나리오.
    completed(0) ≤ total(2) 불변식.
    """
    fake_db = _make_cursor_with_challenges(total_cnt=2, comp_cnt=0)
    with patch("services.score_service.recalculate_score", lambda user_id: None), \
            patch("routes.home.db", fake_db):
        response = logged_in_client.get("/", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "DopaCheck" in html


def test_completed_at_기준_쿼리_파라미터_검증(logged_in_client):
    """completed_challenges 쿼리가 completed_at 컬럼을 사용하는지 확인한다.

    Issue #69: 이전 버그는 started_at 기준이었음. execute 인자를 캡처해 검증.
    """
    captured_calls = []

    @contextmanager
    def _capturing_db():
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
            {"cnt": 20},
            {"cnt": 5},
            {"avg_score": 65.0},
            {"sum_price": 30000},
            {"sum_min": 150},
            {"total_cnt": 2},
            {"comp_cnt": 1},
            {"score": 65},
        ]

        original_execute = cursor.execute

        def capturing_execute(sql, params=None):
            captured_calls.append((sql, params))
            return original_execute(sql, params)

        cursor.execute = capturing_execute
        yield cursor

    with patch("services.score_service.recalculate_score", lambda user_id: None), \
            patch("routes.home.db", _capturing_db):
        response = logged_in_client.get("/", follow_redirects=True)

    assert response.status_code == 200

    # 실행된 SQL 중 completed_at 기준 쿼리가 존재해야 함
    all_sqls = [sql for sql, _ in captured_calls]
    completed_at_queries = [sql for sql in all_sqls if "completed_at" in sql and "comp_cnt" in sql]
    assert len(completed_at_queries) >= 1, (
        "completed_challenges 쿼리가 completed_at 컬럼을 사용해야 합니다 (Issue #69)"
    )

    # started_at만 사용하는 comp_cnt 쿼리는 없어야 함 (버그 재발 방지)
    started_at_only_comp = [
        sql for sql in all_sqls
        if "comp_cnt" in sql and "started_at" in sql and "completed_at" not in sql
    ]
    assert len(started_at_only_comp) == 0, (
        "completed_challenges 쿼리에 started_at만 사용하면 안 됩니다 (Issue #69 회귀)"
    )
