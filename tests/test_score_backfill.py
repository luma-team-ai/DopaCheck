"""백필 함수 단위 테스트 (Issue #175 — 점수 의미 반전 후 과거 행 재계산).

검증 항목:
1. 재계산 정확성 — UPDATE에 전달된 값이 ai.score.calculate 결과와 정확히 일치
2. 옛 양수 보너스가 음수로 교정 — challenge_bonus가 음수(-10)인지 확인
3. 멱등성 — 두 번 실행해도 같은 UPDATE 값
4. 챌린지 테이블 미변경 — user_challenges 에 UPDATE/INSERT 없음(SELECT만)
"""
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, call, patch

import ai.score as ai_score


# ── 공통 픽스처 ──────────────────────────────────────────────────────────────

_WEEK_START = date(2026, 6, 1)

# 원본 집계 값 (배달 20만원, 시간 2100분, 챌린지 2개)
_DELIVERY_TOTAL = 200_000
_TIME_TOTAL_MIN = 2_100
_CHALLENGE_COMPLETED = 2

# 예상 결과 — real ai.score.calculate 사용 (하드코딩 금지)
_EXPECTED = ai_score.calculate({
    "delivery_total": _DELIVERY_TOTAL,
    "time_total_min": _TIME_TOTAL_MIN,
    "challenge_completed": _CHALLENGE_COMPLETED,
})


def _make_cursor(week_start=_WEEK_START):
    """backfill_all_scores 한 사이클에 맞춘 커서 mock.

    fetchall: DISTINCT rows (1건)
    fetchone 순서 (한 row당):
        1. delivery SUM → {"sum_price": ...}
        2. time SUM    → {"sum_min": ...}
        3. challenge COUNT → {"comp_count": ...}
    """
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"user_id": 1, "week_start": week_start}]
    cursor.fetchone.side_effect = [
        {"sum_price": _DELIVERY_TOTAL},
        {"sum_min": _TIME_TOTAL_MIN},
        {"comp_count": _CHALLENGE_COMPLETED},
    ]
    return cursor


@contextmanager
def _mock_db(cursor):
    yield cursor


# ── 테스트 1: 재계산 정확성 ─────────────────────────────────────────────────

def test_백필_재계산_정확성():
    """UPDATE에 전달된 값이 ai.score.calculate 결과와 정확히 일치해야 한다."""
    from services.score_service import backfill_all_scores

    cursor = _make_cursor()

    with patch("services.score_service.db", lambda: _mock_db(cursor)):
        count = backfill_all_scores()

    assert count == 1

    # UPDATE execute 호출 찾기
    update_call = None
    for c in cursor.execute.call_args_list:
        sql = c.args[0]
        if "UPDATE dopamine_scores" in sql:
            update_call = c
            break

    assert update_call is not None, "UPDATE dopamine_scores 호출이 없음"
    params = update_call.args[1]

    assert params[0] == _EXPECTED["score"], f"score 불일치: {params[0]} != {_EXPECTED['score']}"
    assert params[1] == _EXPECTED["delivery_contribution"], (
        f"delivery_contribution 불일치: {params[1]} != {_EXPECTED['delivery_contribution']}"
    )
    assert params[2] == _EXPECTED["time_contribution"], (
        f"time_contribution 불일치: {params[2]} != {_EXPECTED['time_contribution']}"
    )
    assert params[3] == _EXPECTED["challenge_bonus"], (
        f"challenge_bonus 불일치: {params[3]} != {_EXPECTED['challenge_bonus']}"
    )


# ── 테스트 2: 옛 양수 보너스가 음수로 교정 ───────────────────────────────────

def test_챌린지_보너스_음수_교정():
    """challenge_bonus가 반드시 음수(또는 0)여야 한다 — 옛 양수 공식 잔재 교정 검증."""
    from services.score_service import backfill_all_scores

    cursor = _make_cursor()

    with patch("services.score_service.db", lambda: _mock_db(cursor)):
        backfill_all_scores()

    update_call = next(
        c for c in cursor.execute.call_args_list if "UPDATE dopamine_scores" in c.args[0]
    )
    challenge_bonus = update_call.args[1][3]

    assert challenge_bonus == -10, (
        f"challenge_bonus={challenge_bonus} — 챌린지 2개(각 -5)이므로 -10이어야 함"
    )
    assert challenge_bonus < 0, "challenge_bonus는 반드시 음수여야 함 (양수이면 옛 공식 잔재)"


# ── 테스트 3: 멱등성 ─────────────────────────────────────────────────────────

def test_멱등성_두번_실행_동일_결과():
    """동일한 원본 데이터로 두 번 실행해도 UPDATE 파라미터가 같아야 한다."""
    from services.score_service import backfill_all_scores

    def _make_fresh_cursor():
        cursor = _make_cursor()
        return cursor

    results = []
    for _ in range(2):
        cursor = _make_fresh_cursor()
        with patch("services.score_service.db", lambda: _mock_db(cursor)):
            backfill_all_scores()
        update_call = next(
            c for c in cursor.execute.call_args_list if "UPDATE dopamine_scores" in c.args[0]
        )
        results.append(update_call.args[1])

    assert results[0] == results[1], (
        f"1차 실행 파라미터: {results[0]}\n2차 실행 파라미터: {results[1]}\n멱등성 위반"
    )


# ── 테스트 4: 챌린지 테이블 미변경 ──────────────────────────────────────────

def test_챌린지_테이블_미변경():
    """백필 중 user_challenges에 UPDATE/INSERT가 없어야 한다 — SELECT만 허용."""
    from services.score_service import backfill_all_scores

    cursor = _make_cursor()

    with patch("services.score_service.db", lambda: _mock_db(cursor)):
        backfill_all_scores()

    for c in cursor.execute.call_args_list:
        sql = c.args[0].upper()
        if "USER_CHALLENGES" in sql:
            assert sql.strip().startswith("SELECT"), (
                f"user_challenges 에 쓰기(UPDATE/INSERT) 쿼리 감지: {c.args[0]!r}"
            )
