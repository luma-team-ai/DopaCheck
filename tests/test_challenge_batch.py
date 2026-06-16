"""scheduler.challenge_batch.settle_last_week_challenges 단위 테스트."""
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

LAST_WEEK = ("2026-06-08", "2026-06-14")
THIS_WEEK = ("2026-06-15", "2026-06-21")
WEEK_RANGES = (THIS_WEEK, LAST_WEEK)


def _make_db(fetchall_val, fetchone_side_effect):
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall_val
    # 배치는 본 작업 전 GET_LOCK 결과를 먼저 fetchone 한다 → 락 획득 응답을 맨 앞에 주입.
    cursor.fetchone.side_effect = [{"got": 1}, *fetchone_side_effect]

    @contextmanager
    def _db():
        yield cursor

    return _db, cursor


def test_delivery_달성_완료처리():
    """delivery 1회 < target 2 → is_completed=1 업데이트."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-1", "user_id": 1, "started_at": None, "target_type": "delivery", "target_value": 2}],
        [{"cnt": 1}, {"sum_min": 0}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 1
    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE" in str(c)]
    assert any("is_completed = 1" in c for c in update_calls)


def test_delivery_초과_미완료():
    """delivery 3회 >= target 2 → 완료 처리 안 함."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-2", "user_id": 1, "started_at": None, "target_type": "delivery", "target_value": 2}],
        [{"cnt": 3}, {"sum_min": 0}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 0
    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE" in str(c)]
    assert not any("is_completed = 1" in c for c in update_calls)


def test_time_달성_완료처리():
    """time 200분 < target 300분 → is_completed=1."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-3", "user_id": 1, "started_at": None, "target_type": "time", "target_value": 300}],
        [{"cnt": 0}, {"sum_min": 200}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 1


def test_time_경계값_실패():
    """time 300분 == target 300 → 300 < 300 = False → 미완료."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-4", "user_id": 1, "started_at": None, "target_type": "time", "target_value": 300}],
        [{"cnt": 0}, {"sum_min": 300}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 0


def test_both_둘다_달성():
    """both: delivery 1 < 3 AND time_hours 1.0 < 3 → 완료."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-5", "user_id": 1, "started_at": None, "target_type": "both", "target_value": 3}],
        [{"cnt": 1}, {"sum_min": 60}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 1


def test_both_하나라도_초과_미완료():
    """both: delivery 4 >= 3 → 미완료 (AND 조건)."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-6", "user_id": 1, "started_at": None, "target_type": "both", "target_value": 3}],
        [{"cnt": 4}, {"sum_min": 60}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 0


def test_started_at_주중_참여_하한_적용():
    """started_at이 주 시작 이후면 started_at이 delivery 쿼리 하한이 된다."""
    from scheduler.challenge_batch import settle_last_week_challenges

    join_time = datetime(2026, 6, 10, 14, 0, 0)
    _db, cursor = _make_db(
        [{"id": "uc-7", "user_id": 1, "started_at": join_time, "target_type": "delivery", "target_value": 3}],
        [{"cnt": 1}, {"sum_min": 0}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        settle_last_week_challenges()

    delivery_call = [str(c) for c in cursor.execute.call_args_list if "delivery_records" in str(c)][0]
    assert "2026-06-10 14:00:00" in delivery_call


def test_started_at_주시작_이전이면_주시작_기준():
    """started_at이 주 시작 이전이면 gte_at(주 월요일)이 하한이 된다."""
    from scheduler.challenge_batch import settle_last_week_challenges

    join_time = datetime(2026, 6, 1, 0, 0, 0)
    _db, cursor = _make_db(
        [{"id": "uc-8", "user_id": 1, "started_at": join_time, "target_type": "delivery", "target_value": 3}],
        [{"cnt": 0}, {"sum_min": 0}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        settle_last_week_challenges()

    delivery_call = [str(c) for c in cursor.execute.call_args_list if "delivery_records" in str(c)][0]
    assert "2026-06-08 00:00:00" in delivery_call


def test_빈_목록_0반환():
    """활성 챌린지 없으면 0 반환하고 UPDATE 없음."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db([], [])
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 0
    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE" in str(c)]
    assert len(update_calls) == 0


def test_락_미획득시_즉시스킵():
    """GET_LOCK이 0(다른 워커 보유 중)이면 0 반환하고 pending 조회/UPDATE 미실행."""
    from scheduler.challenge_batch import settle_last_week_challenges

    cursor = MagicMock()
    cursor.fetchone.return_value = {"got": 0}

    @contextmanager
    def _db():
        yield cursor

    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        result = settle_last_week_challenges()

    assert result == 0
    calls = [str(c) for c in cursor.execute.call_args_list]
    assert not any("user_challenges uc JOIN" in c for c in calls)
    assert not any("UPDATE" in c for c in calls)


def test_completed_at_지난주_일요일로_설정():
    """완료 처리 시 completed_at이 지난 주 일요일 23:59:59로 기록된다."""
    from scheduler.challenge_batch import settle_last_week_challenges

    _db, cursor = _make_db(
        [{"id": "uc-9", "user_id": 1, "started_at": None, "target_type": "delivery", "target_value": 2}],
        [{"cnt": 0}, {"sum_min": 0}],
    )
    with patch("scheduler.challenge_batch.db", _db), \
         patch("scheduler.challenge_batch.get_week_ranges", return_value=WEEK_RANGES):
        settle_last_week_challenges()

    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE" in str(c)]
    assert any("2026-06-14 23:59:59" in c for c in update_calls)
