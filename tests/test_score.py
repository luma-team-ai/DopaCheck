import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@contextmanager
def _fake_db():
    """score_page 본문 쿼리에 맞춘 커서 mock.

    PR50 score.py의 fetchone 호출 순서:
    1. dopamine_scores SELECT (이번 주 점수/기여도)
    2. COUNT(*) 전체 유저 수 → {"cnt": ...}
    3. COUNT(*) 나보다 높은 유저 수 → {"cnt": ...}
    4. dopamine_scores SELECT (지난주 점수)
    5. SUM(...) 시간 통계 → {"sum_min": ...}
    """
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"score": 72, "delivery_contribution": 28, "time_contribution": 30, "challenge_bonus": 14},
        {"cnt": 20},   # 전체 유저 수
        {"cnt": 5},    # 나보다 점수 높은 유저 수
        {"score": 65},  # 지난주 점수
        {"sum_min": 120},  # 이번 주 시간 사용 총합(분)
    ]
    yield cursor


def test_점수_페이지_렌더링(logged_in_client):
    # recalculate_score는 별도 DB 접속을 일으키므로 no-op 처리하고,
    # 페이지 본문 쿼리만 _fake_db로 mock한다.
    with patch("routes.score.recalculate_score", lambda user_id: None), \
            patch("routes.score.db", _fake_db):
        resp = logged_in_client.get("/score")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        # score/index.html에 실재하는 핵심 문자열 검증 (P2 보강)
        assert "도파민" in body
        assert "상위" in body


def test_점수_산출_입출력():
    """FR-26, FR-27: 0~100 범위, 가중치 40/40/20 검증 (PRD §9) — #48 합의 계산식."""
    from ai.score import calculate

    # 최선(소비 0): 배달 40 + 시간 40 + 보너스 0 = 80
    best = calculate({"delivery_total": 0, "time_total_min": 0, "challenge_completed": 0})
    assert best["delivery_contribution"] == 40
    assert best["time_contribution"] == 40
    assert best["challenge_bonus"] == 0
    assert best["score"] == 80

    # 상한 소비 + 챌린지 4개: 배달 0 + 시간 0 + 보너스 20 = 20
    worst = calculate({"delivery_total": 200_000, "time_total_min": 2_100, "challenge_completed": 4})
    assert worst["delivery_contribution"] == 0
    assert worst["time_contribution"] == 0
    assert worst["challenge_bonus"] == 20
    assert worst["score"] == 20

    # 챌린지 보너스 상한 (min 적용): 100개여도 보너스는 20점
    # 소비 0 + 챌린지 만점 → 40 + 40 + 20 = 100점(만점 경로)
    capped = calculate({"delivery_total": 0, "time_total_min": 0, "challenge_completed": 100})
    assert capped["challenge_bonus"] == 20
    assert capped["score"] == 100

    # score는 항상 0~100 범위, 가중치 합 40/40/20
    for data in (best, worst, capped):
        assert 0 <= data["score"] <= 100
    assert (
        best["delivery_contribution"] + best["time_contribution"] + capped["challenge_bonus"]
    ) == 100


def test_분석_저장시_점수_재산출():
    """FR-31: recalculate_score가 dopamine_scores upsert를 수행하는지 검증."""
    from services.score_service import recalculate_score

    cursor = MagicMock()
    # fetchone 순서: delivery sum → time sum → delivery count → challenge count
    cursor.fetchone.side_effect = [
        {"sum_price": 47_000},
        {"sum_min": 870},
        {"cnt": 3},          # 이번 주 배달 횟수 (챌린지 progress용)
        {"comp_count": 2},   # 진행도 갱신 후 완료 챌린지 수
    ]
    # 활성 챌린지 없음 (user_challenges JOIN 쿼리)
    cursor.fetchall.return_value = []

    @contextmanager
    def _agg_db():
        yield cursor

    with patch("services.score_service.db", _agg_db):
        recalculate_score(user_id=1)

    # 마지막 execute 호출이 dopamine_scores INSERT(upsert)여야 함
    last_sql = cursor.execute.call_args_list[-1].args[0]
    assert "INSERT INTO dopamine_scores" in last_sql
    assert "ON DUPLICATE KEY UPDATE" in last_sql


def test_점수_음수_입력_방어():
    """#60: delivery_total / time_total_min / challenge_completed 음수 입력 시 0 clamp."""
    from ai.score import calculate

    result = calculate({
        "delivery_total": -99999,
        "time_total_min": -500,
        "challenge_completed": -3,
    })
    # 음수를 0으로 clamp → 최선 케이스와 동일 (배달 40 + 시간 40 + 보너스 0 = 80)
    assert result["delivery_contribution"] == 40, "음수 delivery_total은 0으로 clamp되어야 함"
    assert result["time_contribution"] == 40, "음수 time_total_min은 0으로 clamp되어야 함"
    assert result["challenge_bonus"] == 0, "음수 challenge_completed는 0으로 clamp되어야 함"
    assert result["score"] == 80
    assert result["success"] is True
