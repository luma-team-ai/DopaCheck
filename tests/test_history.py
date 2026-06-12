"""히스토리 테스트 (담당: 허남 — FR-21~25). MariaDB(pymysql) 기준 (#21)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

# record_id는 UUID 형식 검증을 통과해야 하므로 유효한 UUID 사용
REC_DELIVERY = "00000000-0000-0000-0000-0000000000a1"
REC_TIME = "00000000-0000-0000-0000-0000000000a2"
REC_MISSING = "00000000-0000-0000-0000-0000000000ff"

# logged_in_client 가 주입하는 세션 user_id (conftest.py와 일치)
SESSION_USER_ID = 1


def _patch_db(cursor):
    """routes.history.db 를 주어진 cursor를 yield하는 컨텍스트매니저로 교체한다.

    실제 db()는 @contextmanager 라서 `with db() as cursor:` 형태로 쓰인다.
    """
    @contextmanager
    def fake_db():
        yield cursor

    return patch("routes.history.db", fake_db)


def _make_cursor(fetchall=None, fetchone=None, fetchall_side_effect=None,
                 fetchone_side_effect=None):
    cursor = MagicMock()
    if fetchall_side_effect is not None:
        cursor.fetchall.side_effect = fetchall_side_effect
    else:
        cursor.fetchall.return_value = fetchall if fetchall is not None else []
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    else:
        cursor.fetchone.return_value = fetchone
    return cursor


def test_히스토리_목록_렌더링(logged_in_client):
    """FR-21: 목록 페이지가 200으로 응답한다."""
    cursor = _make_cursor(fetchall_side_effect=[[], []])  # delivery, time
    with _patch_db(cursor):
        res = logged_in_client.get("/history")
    assert res.status_code == 200


def test_기간_필터_week(logged_in_client):
    """FR-24: ?period=week — created_at >= cutoff 파라미터가 바인딩된다."""
    cursor = _make_cursor(fetchall_side_effect=[[], []])
    with _patch_db(cursor):
        res = logged_in_client.get("/history?period=week")
    assert res.status_code == 200
    # week 분기에서는 cutoff 파라미터가 추가되어 user_id 외 1개 더 바인딩된다.
    first_call = cursor.execute.call_args_list[0]
    sql, params = first_call.args
    assert "user_id = %s" in sql
    assert "created_at >= %s" in sql
    assert params[0] == SESSION_USER_ID
    assert len(params) == 2


def test_기간_필터_month(logged_in_client):
    """FR-24: ?period=month 파라미터가 정상 처리된다."""
    cursor = _make_cursor(fetchall_side_effect=[[], []])
    with _patch_db(cursor):
        res = logged_in_client.get("/history?period=month")
    assert res.status_code == 200


def test_목록_user_id_스코프_적용(logged_in_client):
    """RLS 대체: 목록 쿼리에 WHERE user_id = %s + 세션 user_id 바인딩."""
    cursor = _make_cursor(fetchall_side_effect=[[], []])
    with _patch_db(cursor):
        res = logged_in_client.get("/history")
    assert res.status_code == 200
    for call in cursor.execute.call_args_list:
        sql, params = call.args
        assert "WHERE user_id = %s" in sql
        assert params[0] == SESSION_USER_ID


def test_상세_조회_delivery(logged_in_client):
    """FR-22: delivery 타입 상세 페이지가 200으로 응답한다."""
    fake_record = {
        "id": REC_DELIVERY,
        "user_id": SESSION_USER_ID,
        "total_price": 21000,
        "delivery_fee": 3000,
        "total_calories": 1940,
        "items": [{"name": "후라이드치킨", "price": 18000, "quantity": 1, "calories": 1800}],
        "ai_comment": "맛있게 드셨나요?",
        "created_at": "2026-06-12T12:00:00+00:00",
    }
    cursor = _make_cursor(fetchone=fake_record)
    with _patch_db(cursor):
        res = logged_in_client.get(f"/history/{REC_DELIVERY}?type=delivery")
    assert res.status_code == 200


def test_상세_조회_time(logged_in_client):
    """FR-22: time 타입 상세 페이지가 200으로 응답한다."""
    fake_record = {
        "id": REC_TIME,
        "user_id": SESSION_USER_ID,
        "youtube_min": 120,
        "instagram_min": 60,
        "tiktok_min": 30,
        "game_min": 90,
        "hourly_wage": 10030,
        "ai_comment": "오늘도 열심히 스크롤 하셨군요!",
        "created_at": "2026-06-12T14:00:00+00:00",
    }
    cursor = _make_cursor(fetchone=fake_record)
    with _patch_db(cursor):
        res = logged_in_client.get(f"/history/{REC_TIME}?type=time")
    assert res.status_code == 200


def test_상세_조회_없는_기록(logged_in_client):
    """FR-22: 존재하지 않는 기록 조회 시 404 응답."""
    cursor = _make_cursor(fetchone=None)
    with _patch_db(cursor):
        res = logged_in_client.get(f"/history/{REC_MISSING}?type=delivery")
    assert res.status_code == 404


def test_기록_삭제_성공(logged_in_client):
    """FR-23: 본인 기록 삭제 시 204 No Content 응답."""
    # select(존재) → delete 순으로 fetchone 1회 호출
    cursor = _make_cursor(fetchone={"id": REC_DELIVERY})
    with _patch_db(cursor):
        res = logged_in_client.delete(f"/history/{REC_DELIVERY}?type=delivery")
    assert res.status_code == 204
    assert res.data == b""


def test_기록_삭제_타인_차단(logged_in_client):
    """FR-23: 타인 기록 삭제 시도 시 404로 차단된다."""
    cursor = _make_cursor(fetchone=None)
    with _patch_db(cursor):
        res = logged_in_client.delete(f"/history/{REC_MISSING}?type=delivery")
    assert res.status_code == 404


def test_상세_잘못된_uuid_400(logged_in_client):
    """P2: UUID 형식이 아닌 record_id는 400으로 차단된다."""
    res = logged_in_client.get("/history/not-a-uuid?type=delivery")
    assert res.status_code == 400


def test_삭제_잘못된_uuid_400(logged_in_client):
    """P2: UUID 형식이 아닌 record_id 삭제 시도는 400으로 차단된다."""
    res = logged_in_client.delete("/history/not-a-uuid-value?type=delivery")
    assert res.status_code == 400


def test_삭제_쿼리에_user_id_필터_포함(logged_in_client):
    """P2(IDOR): select·delete 쿼리 모두 user_id 필터 + 세션 user_id 바인딩."""
    cursor = _make_cursor(fetchone={"id": REC_DELIVERY})
    with _patch_db(cursor):
        res = logged_in_client.delete(f"/history/{REC_DELIVERY}?type=delivery")

    assert res.status_code == 204
    # select + delete 두 execute 모두 user_id 필터와 세션 user_id 바인딩
    assert len(cursor.execute.call_args_list) == 2
    for call in cursor.execute.call_args_list:
        sql, params = call.args
        assert "user_id = %s" in sql
        assert SESSION_USER_ID in params
    delete_sql = cursor.execute.call_args_list[1].args[0]
    assert delete_sql.strip().upper().startswith("DELETE")


def test_목록_잘못된_type_filter_400(logged_in_client):
    """P2: 허용되지 않은 type_filter 값은 400으로 차단된다."""
    res = logged_in_client.get("/history?type_filter=injection_string")
    assert res.status_code == 400


def test_period_임의값_all로_정규화(logged_in_client):
    """P2: 허용되지 않은 period 값은 'all'로 정규화되어 200 응답."""
    cursor = _make_cursor(fetchall_side_effect=[[], []])
    with _patch_db(cursor):
        res = logged_in_client.get("/history?period=evil")
    assert res.status_code == 200
    # 'all'로 정규화되면 cutoff 없이 user_id 1개만 바인딩
    sql, params = cursor.execute.call_args_list[0].args
    assert "created_at >= %s" not in sql
    assert len(params) == 1


def test_비로그인_접근_차단(client):
    """FR-0: 비로그인 시 /login으로 리다이렉트."""
    res = client.get("/history")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_week_month_경계_KST_공통유틸_사용():
    """#11: _week_start/_month_start가 KST 기준(공통 utils.week)으로 계산된다.

    서버 로컬(date.today())이 아닌 KST 날짜를 써야 자정 부근 하루 오차가 없다.
    kst_today를 고정해 월요일 시작·1일 시작이 정확히 산출되는지 검증한다.
    """
    from datetime import date
    import routes.history as h

    # 2026-06-12(금) → 같은 주 월요일은 2026-06-08
    with patch.object(h, "kst_today", lambda: date(2026, 6, 12)):
        assert h._week_start() == "2026-06-08"
        assert h._month_start() == "2026-06-01"
        assert h._date_label(date(2026, 6, 12)) == "오늘, 6월 12일"
        assert h._date_label(date(2026, 6, 11)) == "어제, 6월 11일"
        assert h._date_label(date(2026, 6, 9)) == "6월 9일"
