"""히스토리 테스트 (담당: 허남 — FR-21~25)."""
from unittest.mock import MagicMock, patch

# record_id는 UUID 형식 검증을 통과해야 하므로 유효한 UUID 사용
REC_DELIVERY = "00000000-0000-0000-0000-0000000000a1"
REC_TIME = "00000000-0000-0000-0000-0000000000a2"
REC_MISSING = "00000000-0000-0000-0000-0000000000ff"


def test_히스토리_목록_렌더링(logged_in_client):
    """FR-21: 목록 페이지가 200으로 응답한다."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get("/history")
    assert res.status_code == 200


def test_기간_필터_week(logged_in_client):
    """FR-24: ?period=week 파라미터가 정상 처리된다."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get("/history?period=week")
    assert res.status_code == 200


def test_기간_필터_month(logged_in_client):
    """FR-24: ?period=month 파라미터가 정상 처리된다."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get("/history?period=month")
    assert res.status_code == 200


def test_상세_조회_delivery(logged_in_client):
    """FR-22: delivery 타입 상세 페이지가 200으로 응답한다."""
    fake_record = {
        "id": REC_DELIVERY,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "total_price": 21000,
        "delivery_fee": 3000,
        "total_calories": 1940,
        "items": [{"name": "후라이드치킨", "price": 18000, "quantity": 1, "calories": 1800}],
        "ai_comment": "맛있게 드셨나요?",
        "created_at": "2026-06-12T12:00:00+00:00",
    }
    mock_result = MagicMock()
    mock_result.data = [fake_record]

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get(f"/history/{REC_DELIVERY}?type=delivery")
    assert res.status_code == 200


def test_상세_조회_time(logged_in_client):
    """FR-22: time 타입 상세 페이지가 200으로 응답한다."""
    fake_record = {
        "id": REC_TIME,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "youtube_min": 120,
        "instagram_min": 60,
        "tiktok_min": 30,
        "game_min": 90,
        "hourly_wage": 10030,
        "ai_comment": "오늘도 열심히 스크롤 하셨군요!",
        "created_at": "2026-06-12T14:00:00+00:00",
    }
    mock_result = MagicMock()
    mock_result.data = [fake_record]

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get(f"/history/{REC_TIME}?type=time")
    assert res.status_code == 200


def test_상세_조회_없는_기록(logged_in_client):
    """FR-22: 존재하지 않는 기록 조회 시 404 응답."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get(f"/history/{REC_MISSING}?type=delivery")
    assert res.status_code == 404


def test_기록_삭제_성공(logged_in_client):
    """FR-23: 본인 기록 삭제 시 204 No Content 응답."""
    mock_existing = MagicMock()
    mock_existing.data = [{"id": REC_DELIVERY}]
    mock_delete = MagicMock()
    mock_delete.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.execute.side_effect = [mock_existing, mock_delete]

        res = logged_in_client.delete(f"/history/{REC_DELIVERY}?type=delivery")
    assert res.status_code == 204
    assert res.data == b""


def test_기록_삭제_타인_차단(logged_in_client):
    """FR-23: 타인 기록 삭제 시도 시 404로 차단된다."""
    mock_existing = MagicMock()
    mock_existing.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_existing

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
    """P2(IDOR): delete 쿼리에 user_id eq 필터가 적용된다."""
    mock_existing = MagicMock()
    mock_existing.data = [{"id": REC_DELIVERY}]
    mock_delete = MagicMock()
    mock_delete.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.execute.side_effect = [mock_existing, mock_delete]

        res = logged_in_client.delete(f"/history/{REC_DELIVERY}?type=delivery")

    assert res.status_code == 204
    # delete 체인에서 user_id 필터가 호출됐는지 확인
    eq_calls = [c.args for c in mock_table.eq.call_args_list]
    assert ("user_id", "00000000-0000-0000-0000-000000000001") in eq_calls


def test_목록_잘못된_type_filter_400(logged_in_client):
    """P2: 허용되지 않은 type_filter 값은 400으로 차단된다."""
    res = logged_in_client.get("/history?type_filter=injection_string")
    assert res.status_code == 400


def test_period_임의값_all로_정규화(logged_in_client):
    """P2: 허용되지 않은 period 값은 'all'로 정규화되어 200 응답."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("routes.history.get_supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = mock_result

        res = logged_in_client.get("/history?period=evil")
    assert res.status_code == 200


def test_비로그인_접근_차단(client):
    """FR-0: 비로그인 시 /login으로 리다이렉트."""
    res = client.get("/history")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
