"""scripts.audit_time_target_values.audit 단위 테스트 (#161 후속)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


def _make_db(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.rowcount = 1

    @contextmanager
    def _db():
        yield cursor

    return _db, cursor


def test_고신뢰_오염_분류():
    """1200분 초과 + 60배수 → suspect, 현실범위 60배수 → ambiguous."""
    from scripts.audit_time_target_values import audit

    rows = [
        {"id": "a", "title": "오염", "target_value": 3600, "participants": 2},  # 60×60 → suspect
        {"id": "b", "title": "정상범위", "target_value": 300, "participants": 1},  # ambiguous
        {"id": "c", "title": "비배수", "target_value": 130, "participants": 0},  # 무시
    ]
    _db, _ = _make_db(rows)
    with patch("scripts.audit_time_target_values.db", _db):
        result = audit(fix=False)

    assert result == {"total": 3, "suspect": 1, "ambiguous": 1, "fixed": 0}


def test_fix_고신뢰_오염만_교정():
    """--fix 는 suspect 행만 ÷60 UPDATE, ambiguous 는 건드리지 않는다."""
    from scripts.audit_time_target_values import audit

    rows = [
        {"id": "a", "title": "오염", "target_value": 5400, "participants": 1},  # 90×60 → 90 복원
        {"id": "b", "title": "정상", "target_value": 600, "participants": 1},   # ambiguous
    ]
    _db, cursor = _make_db(rows)
    with patch("scripts.audit_time_target_values.db", _db):
        result = audit(fix=True)

    assert result["suspect"] == 1
    assert result["fixed"] == 1
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE" in str(c)]
    assert len(update_calls) == 1
    # 5400 ÷ 60 = 90 으로 교정
    assert update_calls[0].args[1][0] == 90
    assert update_calls[0].args[1][1] == "a"


def test_fix_없으면_UPDATE_안함():
    """점검 모드(fix=False)에서는 UPDATE 쿼리가 나가지 않는다."""
    from scripts.audit_time_target_values import audit

    rows = [{"id": "a", "title": "오염", "target_value": 3600, "participants": 0}]
    _db, cursor = _make_db(rows)
    with patch("scripts.audit_time_target_values.db", _db):
        audit(fix=False)

    assert not any("UPDATE" in str(c) for c in cursor.execute.call_args_list)
