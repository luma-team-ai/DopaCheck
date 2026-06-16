"""관리자 인가 회귀 방어 테스트 (FR-54~58).

검증 항목:
  1. 비로그인 접근 → 로그인 페이지 302 리다이렉트 (DB 호출 없음)
  2. role='user' 로그인 → 홈('/')으로 302 리다이렉트 (대시보드 미렌더)
  3. role='admin' 로그인 → 200 응답 + 대시보드 렌더
  4. 권한 강등 즉시 반영 → 세션에 role 흔적 있어도 DB 기준으로 차단
"""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_db_mock(role_row=None):
    """admin_required 의 첫 번째 fetchone(role 조회)만 처리하는 단순 mock.

    role_row: {"role": "admin"} 등. None 이면 user 없음으로 처리(role='user').
    """
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = role_row

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


def _make_admin_db_mock():
    """role='admin' 케이스용 mock.

    admin_required(role 조회) + admin_dashboard(통계 쿼리) 모두 처리한다.
    fetchone 호출 순서:
      0. role 조회         → {"role": "admin"}
      1. total_users       → {"cnt": 10}
      2. active_users      → {"cnt": 5}
      3. delivery_count    → {"cnt": 20}
      4. time_count        → {"cnt": 15}
      5. total_price       → {"sum_price": 300000}
      6. total_min         → {"sum_min": 600}
      7. score_stats       → {"avg_score": 50, "max_score": 90, "min_score": 10}
      8. distribution      → {"g1":1,"g2":2,"g3":3,"g4":2,"g5":1}
      9. challenge_total   → {"total": 10}
     10. challenge_completed → {"completed": 7}
    fetchall:
      ranking_list         → [{"nickname":"홍길동","top_score":90,"email":"test@example.com"}]
    """
    fetchone_seq = [
        {"role": "admin"},
        {"cnt": 10},
        {"cnt": 5},
        {"cnt": 20},
        {"cnt": 15},
        {"sum_price": 300000},
        {"sum_min": 600},
        {"avg_score": 50, "max_score": 90, "min_score": 10},
        {"g1": 1, "g2": 2, "g3": 3, "g4": 2, "g5": 1},
        {"total": 10},
        {"completed": 7},
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = fetchone_seq
    # ranking_list — email은 "@" 포함이어야 _mask_email이 안 깨짐
    mock_cursor.fetchall.return_value = [
        {"nickname": "홍길동", "top_score": 90, "email": "test@example.com"}
    ]

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

def test_비로그인_접근_로그인_리다이렉트(client):
    """[TC-1] 세션에 user_id 없는 상태로 /admin 접근 → 로그인 페이지 302.

    login_required 가 DB 호출 전에 차단하므로 db()는 호출되지 않아야 한다.
    """
    mock_db = MagicMock()

    with patch("routes.admin.db", mock_db):
        res = client.get("/admin")

    assert res.status_code == 302
    # /login 으로 리다이렉트 확인
    assert "/login" in res.headers["Location"]
    # DB 컨텍스트매니저 자체가 호출되지 않아야 함
    mock_db.assert_not_called()


def test_role_user_홈_리다이렉트(logged_in_client):
    """[TC-2] role='user' 인 계정이 /admin 접근 → 홈('/')으로 302 리다이렉트.

    대시보드 render_template 은 호출되면 안 된다.
    """
    with patch("routes.admin.db", _make_db_mock(role_row={"role": "user"})), \
         patch("routes.admin.render_template") as mock_render:
        res = logged_in_client.get("/admin")

    assert res.status_code == 302
    assert res.headers["Location"].endswith("/") or "home" in res.headers["Location"]
    mock_render.assert_not_called()


def test_role_admin_대시보드_200(logged_in_client):
    """[TC-3] role='admin' 인 계정이 /admin 접근 → 200 + 대시보드 렌더.

    render_template 을 mock 해서 템플릿 파일 없이도 상태코드와 호출 대상을 검증한다.
    """
    with patch("routes.admin.db", _make_admin_db_mock()), \
         patch("routes.admin.render_template", return_value="OK") as mock_render:
        res = logged_in_client.get("/admin")

    assert res.status_code == 200
    # admin/index.html 로 렌더됐는지 확인
    mock_render.assert_called_once()
    call_args = mock_render.call_args
    assert call_args[0][0] == "admin/index.html", (
        f"admin/index.html 로 렌더돼야 하는데 {call_args[0][0]} 으로 렌더됨"
    )


def _make_users_list_db_mock(filter_cnt=10):
    """users_list 라우트용 DB mock.

    fetchone 호출 순서:
      0. admin_required role 조회 → {"role": "admin"}
      1. total_users              → {"cnt": 50}
      2. new_users (7일)          → {"cnt": 5}
      3. danger_users             → {"cnt": 3}
      4. filtered_count           → {"cnt": filter_cnt}
    fetchall: 유저 목록 → []
    """
    seq = [
        {"role": "admin"},
        {"cnt": 50},
        {"cnt": 5},
        {"cnt": 3},
        {"cnt": filter_cnt},
    ]
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = seq
    mock_cursor.fetchall.return_value = []

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


def test_users_list_전체_필터_200(logged_in_client):
    """[TC-5] /admin/users?filter=all → 200, 필터 칩 링크 존재 확인."""
    with patch("routes.admin.db", _make_users_list_db_mock()):
        res = logged_in_client.get("/admin/users?filter=all")
    assert res.status_code == 200
    body = res.data.decode()
    assert "filter=recent" in body
    assert "filter=danger" in body
    assert "filter=challenge" in body


def _make_filter_db_mock(filter_cnt: int):
    """filter SQL 검증용 공통 DB mock — call_args_list로 실제 전달 SQL 검증."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"role": "admin"},
        {"cnt": 50},
        {"cnt": 5},
        {"cnt": 3},
        {"cnt": filter_cnt},
    ]
    mock_cursor.fetchall.return_value = []

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db, mock_cursor


def test_users_list_danger_필터_SQL_적용(logged_in_client):
    """[TC-6] /admin/users?filter=danger → cursor.execute에 dopamine_scores 조건 전달."""
    mock_db, mock_cursor = _make_filter_db_mock(filter_cnt=3)
    with patch("routes.admin.db", mock_db):
        res = logged_in_client.get("/admin/users?filter=danger")
    assert res.status_code == 200
    all_sqls = " ".join(str(call.args[0]) for call in mock_cursor.execute.call_args_list)
    assert "dopamine_scores" in all_sqls, "danger 필터 WHERE 조건이 SQL에 없음"


def test_users_list_recent_필터_SQL_적용(logged_in_client):
    """[TC-7] /admin/users?filter=recent → cursor.execute에 created_at >= 조건 전달."""
    mock_db, mock_cursor = _make_filter_db_mock(filter_cnt=2)
    with patch("routes.admin.db", mock_db):
        res = logged_in_client.get("/admin/users?filter=recent")
    assert res.status_code == 200
    all_sqls = " ".join(str(call.args[0]) for call in mock_cursor.execute.call_args_list)
    assert "created_at >=" in all_sqls, "recent 필터 WHERE 조건이 SQL에 없음"


def test_권한강등_즉시반영_세션캐시_무효(logged_in_client):
    """[TC-4] 세션에 role='admin' 흔적이 있어도 DB가 'user' 반환하면 즉시 차단.

    인가 판단이 세션 캐시가 아닌 매 요청마다 DB를 기준으로 함을 검증한다.
    """
    # 세션에 role='admin' 을 심어둠 (강등 전 로그인 상태 재현)
    with logged_in_client.session_transaction() as sess:
        sess["role"] = "admin"

    with patch("routes.admin.db", _make_db_mock(role_row={"role": "user"})), \
         patch("routes.admin.render_template") as mock_render:
        res = logged_in_client.get("/admin")

    assert res.status_code == 302, (
        "세션에 role='admin' 이 있어도 DB가 'user' 반환하면 홈으로 차단돼야 함"
    )
    mock_render.assert_not_called()
