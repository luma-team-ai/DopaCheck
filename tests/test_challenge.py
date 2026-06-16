"""챌린지 테스트 (담당: 오영석)."""
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


def _make_db_mock(fetchall=None, fetchone=None):
    """db() 컨텍스트매니저 mock — cursor.fetchall/fetchone 반환값 지정."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall if fetchall is not None else []
    mock_cursor.fetchone.return_value = fetchone

    @contextmanager
    def mock_db():
        yield mock_cursor

    return mock_db


def test_챌린지_페이지_렌더링(logged_in_client):
    """FR-32: 챌린지 목록 페이지가 200으로 응답한다."""
    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.get("/challenge")
    assert res.status_code == 200


def test_챌린지_중복참여_차단(logged_in_client):
    """FR-35: 이미 참여 중인 챌린지에 재참여 시 409 반환."""
    challenge_id = "00000000-0000-0000-0000-000000000001"

    # CSRF 토큰 세션 주입
    with logged_in_client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    with patch("routes.challenge.db", _make_db_mock(fetchone={"id": "existing-uc"})):
        res = logged_in_client.post(
            f"/challenge/{challenge_id}/join",
            headers={"X-CSRF-Token": "test-csrf-token"},
        )

    assert res.status_code == 409
    assert "이미 참여" in res.get_json()["error"]


def test_챌린지_참여_성공_201(logged_in_client):
    """FR-34: 유효 UUID·미참여 상태에서 참여하면 201과 INSERT가 수행된다 (#133 회귀 방지)."""
    challenge_id = "00000000-0000-0000-0000-000000000001"

    with logged_in_client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    # 활성 참여 없음(fetchone=None) → INSERT 후 201
    mock_db = _make_db_mock(fetchone=None)
    with patch("routes.challenge.db", mock_db):
        res = logged_in_client.post(
            f"/challenge/{challenge_id}/join",
            headers={"X-CSRF-Token": "test-csrf-token"},
        )

    assert res.status_code == 201
    assert res.get_json()["success"] is True


def test_챌린지_참여_잘못된_UUID_400(logged_in_client):
    """#134 P2-A: 비 UUID challenge_id는 FK 위반 전에 400으로 조기 반환한다."""
    with logged_in_client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    # DB 접근 전에 400으로 차단되어야 하므로 mock은 호출되지 않아야 함
    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.post(
            "/challenge/not-a-uuid/join",
            headers={"X-CSRF-Token": "test-csrf-token"},
        )

    assert res.status_code == 400
    assert "잘못된 챌린지 ID" in res.get_json()["error"]


def test_top_app_전부_0이면_recommend_history에서_제외(logged_in_client):
    """app_totals 합계가 0이면 top_app/top_app_hours 없이 recommend 호출된다."""
    call_count = [0]

    @contextmanager
    def mock_db_seq():
        cursor = MagicMock()

        def fetchone_side():
            call_count[0] += 1
            # has_delivery=있음, has_time=없음(None)
            return {"id": "x"} if call_count[0] == 1 else None

        cursor.fetchone.side_effect = fetchone_side
        cursor.fetchall.side_effect = [
            # challenges 목록
            [],
            # user_challenges
            [],
            # has_delivery / has_time 체크 이후 delivery_rows
            [{"created_at": "2024-01-01"}],
            # time_rows — 전부 0
            [{"youtube_min": 0, "instagram_min": 0, "tiktok_min": 0, "game_min": 0}],
        ]
        yield cursor

    captured = {}

    def fake_recommend(history):
        captured["history"] = history
        return {"recommendations": []}

    # AI 추천 캐시 무효화
    with logged_in_client.session_transaction() as sess:
        sess.pop("ai_recommendations", None)
        sess.pop("ai_recommendations_ts", None)

    with patch("routes.challenge.db", mock_db_seq), \
         patch("routes.challenge.ai_challenge.recommend", fake_recommend):
        res = logged_in_client.get("/challenge")

    assert res.status_code == 200
    assert "top_app" not in captured.get("history", {}), \
        "합계 0이면 top_app이 history에 포함되면 안 됨"


from datetime import date as _date


def _run_recalc(active_challenges, *, score_aggr, judge_aggr, judge_today):
    """recalculate_score를 모킹 환경에서 실행하고 cursor를 반환한다.

    fetchone 실행 순서(코드와 일치):
      1) sum_price(점수용 배달 총액)
      2) sum_min(점수용 시간 총합)
      3) cnt(점수용 이번 주 배달 횟수)
      4) [fetchall] active_challenges
      5) judge cnt(judge_week 배달 횟수)
      6) judge sum_min(judge_week 시간 총합)
      7) comp_count(이번 주 완료 챌린지 수)

    Args:
        score_aggr: (sum_price, sum_min, cnt) — 점수용 이번 주 집계.
        judge_aggr: (judge_cnt, judge_sum_min) — judge_week 집계.
        judge_today: kst_today가 반환할 date(일요일/월요일/주중 모킹용).
    """
    from services.score_service import recalculate_score

    sum_price, sum_min, cnt = score_aggr
    judge_cnt, judge_sum_min = judge_aggr

    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"sum_price": sum_price},
        {"sum_min": sum_min},
        {"cnt": cnt},
        {"cnt": judge_cnt},          # _aggregate_counts: judge 배달 횟수
        {"sum_min": judge_sum_min},  # _aggregate_counts: judge 시간 총합
        {"comp_count": 1},
    ]
    cursor.fetchall.return_value = active_challenges

    @contextmanager
    def _db():
        yield cursor

    with patch("services.score_service.db", _db), \
         patch("services.score_service.kst_today", lambda: judge_today):
        recalculate_score(user_id=1)

    return cursor


def _completed(cursor) -> bool:
    """is_completed=1 UPDATE가 호출됐는지 여부."""
    calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE user_challenges" in str(c)]
    return any("is_completed = 1" in c for c in calls)


# ── judge_week 기준: 2026-06-16(화)이 today일 때 이번 주=6/15~6/21, 지난주=6/8~6/14
_TUE = _date(2026, 6, 16)   # 주중(화) — 이번 주 미종료
_MON = _date(2026, 6, 15)   # 월요일 — 이번 주 시작 = 지난주(6/8~6/14)로 판정
_SUN = _date(2026, 6, 21)   # 일요일 — 이번 주 종료일 → 이번 주로 판정


def test_챌린지_일요일_이번주_달성시_완료처리():
    """(a) 일요일: 이번 주 count ≤ tv → 완료. (FR-37, FR-38)"""
    cursor = _run_recalc(
        [{"id": "uc-1", "target_type": "delivery", "target_value": 2}],
        score_aggr=(20_000, 0, 2),
        judge_aggr=(2, 0),   # 일요일 → judge_week=이번 주, 배달 2회 ≤ 2 → 완료
        judge_today=_SUN,
    )
    assert _completed(cursor), "일요일 이번 주 배달 2회 ≤ 2 → 완료여야 함"


def test_챌린지_월요일_지난주_달성시_완료처리():
    """(b) 월요일: 지난주 count ≤ tv → 완료 (이번 주 미접속 회귀 차단, #194 P1-B)."""
    cursor = _run_recalc(
        [{"id": "uc-1", "target_type": "delivery", "target_value": 2}],
        # 이번 주(점수용)는 0건이지만 judge_week=지난주는 2회 → 지난주 기준 완료
        score_aggr=(0, 0, 0),
        judge_aggr=(2, 0),
        judge_today=_MON,
    )
    assert _completed(cursor), "월요일엔 지난주(완전히 끝난 주) 기준으로 완료 판정돼야 함"


def test_챌린지_주중_이번주_미종료시_미완료():
    """(c) 주중(화): 이번 주 미종료 → judge_week=지난주, 지난주 미달성이면 완료 안 됨."""
    cursor = _run_recalc(
        [{"id": "uc-1", "target_type": "delivery", "target_value": 2}],
        # 이번 주는 0건(달성처럼 보이지만), judge_week=지난주는 5회 → 미달성
        score_aggr=(0, 0, 0),
        judge_aggr=(5, 0),
        judge_today=_TUE,
    )
    assert not _completed(cursor), "주중엔 미종료 이번 주가 아닌 지난주 기준이며 지난주 미달성이면 완료 금지"


def test_챌린지_경계_count_eq_tv_완료():
    """(d) <= 경계: count == tv → 완료 (delivery 기준)."""
    cursor = _run_recalc(
        [{"id": "uc-1", "target_type": "delivery", "target_value": 3}],
        score_aggr=(0, 0, 3),
        judge_aggr=(3, 0),   # 3 == tv(3) → 완료
        judge_today=_SUN,
    )
    assert _completed(cursor), "count == tv → 완료여야 함"


def test_챌린지_경계_count_tv_plus_1_미완료():
    """(d) <= 경계: count == tv+1 → 미완료 (delivery 기준)."""
    cursor = _run_recalc(
        [{"id": "uc-1", "target_type": "delivery", "target_value": 3}],
        score_aggr=(0, 0, 4),
        judge_aggr=(4, 0),   # 4 == tv+1 → 미완료
        judge_today=_SUN,
    )
    assert not _completed(cursor), "count == tv+1 → 완료되면 안 됨"


def test_time_챌린지_분단위_임계값_달성():
    """time 챌린지: judge_week time_total_min ≤ tv(분) 시 완료 처리."""
    cursor = _run_recalc(
        [{"id": "uc-time-1", "target_type": "time", "target_value": 300}],
        score_aggr=(0, 0, 0),
        judge_aggr=(0, 300),   # 300분 == tv(300) → 완료
        judge_today=_SUN,
    )
    assert _completed(cursor), "time: 300분 ≤ 300 → 완료여야 함"


def test_time_챌린지_분단위_미달성():
    """time 챌린지: judge_week time_total_min > tv면 미완료로 progress만 갱신."""
    cursor = _run_recalc(
        [{"id": "uc-time-2", "target_type": "time", "target_value": 300}],
        score_aggr=(0, 0, 0),
        judge_aggr=(0, 360),   # 360분 > 300 → 미달성
        judge_today=_SUN,
    )
    assert not _completed(cursor), "time: 360분 > 300 → 완료되면 안 됨"
    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE user_challenges" in str(c)]
    assert any("UPDATE user_challenges" in c for c in update_calls), \
        "미달성 시에도 progress UPDATE는 호출돼야 함"


def test_both_챌린지_float_경계_미달성():
    """both 타입: 시간 단위 float 경계 — tv=3, time_hours=3.1(186분) → 미완료."""
    cursor = _run_recalc(
        [{"id": "uc-both-1", "target_type": "both", "target_value": 3}],
        score_aggr=(0, 0, 0),
        # 배달 3회는 ≤ 3 OK, 시간 186분=3.1h > 3 → int() 절삭 없이 float 비교로 미달성
        judge_aggr=(3, 186),
        judge_today=_SUN,
    )
    assert not _completed(cursor), "both: 3.1h > 3 → 완료되면 안 됨(float 비교)"


# ── P2 추가 테스트 ────────────────────────────────────────

def test_CSRF_토큰_불일치시_403(logged_in_client):
    """CSRF 토큰이 일치하지 않으면 403을 반환한다."""
    challenge_id = "00000000-0000-0000-0000-000000000001"

    # 세션에 토큰 주입 후, 다른 값으로 요청
    with logged_in_client.session_transaction() as sess:
        sess["csrf_token"] = "correct-token"

    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.post(
            f"/challenge/{challenge_id}/join",
            headers={"X-CSRF-Token": "wrong-token"},
        )

    assert res.status_code == 403


def test_CSRF_토큰_없으면_403(logged_in_client):
    """CSRF 토큰 헤더가 아예 없으면 403을 반환한다."""
    challenge_id = "00000000-0000-0000-0000-000000000001"

    with logged_in_client.session_transaction() as sess:
        sess["csrf_token"] = "some-token"

    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.post(f"/challenge/{challenge_id}/join")

    assert res.status_code == 403


def test_AI_추천_캐시_TTL_내_재사용(logged_in_client):
    """AI 추천 캐시가 TTL 내에 있으면 LLM을 재호출하지 않는다."""
    cached_recs = [{"title": "캐시된 추천", "description": "test", "target_type": "delivery", "target_value": 2}]
    now = time.time()

    with logged_in_client.session_transaction() as sess:
        sess["ai_recommendations"] = cached_recs
        sess["ai_recommendations_ts"] = now  # 방금 캐시됨
        sess["ai_recommendations_uid"] = 1

    call_count = [0]

    def fake_recommend(history):
        call_count[0] += 1
        return {"recommendations": []}

    with patch("routes.challenge.db", _make_db_mock()), \
         patch("routes.challenge.ai_challenge.recommend", fake_recommend):
        res = logged_in_client.get("/challenge")

    assert res.status_code == 200
    assert call_count[0] == 0, "TTL 내 캐시 적중 시 LLM 호출 금지"


def test_AI_추천_캐시_TTL_만료시_재호출(logged_in_client):
    """캐시 타임스탬프가 TTL을 초과하면 LLM을 재호출한다."""
    from config import AI_RECOMMEND_CACHE_TTL

    old_ts = time.time() - AI_RECOMMEND_CACHE_TTL - 1  # 만료된 캐시

    with logged_in_client.session_transaction() as sess:
        sess["ai_recommendations"] = [{"title": "오래된 캐시"}]
        sess["ai_recommendations_ts"] = old_ts
        sess["ai_recommendations_uid"] = 1

    call_count = [0]

    @contextmanager
    def mock_db_seq():
        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": "x"}
        cursor.fetchall.side_effect = [
            [],   # challenges
            [],   # user_challenges
            [{"created_at": "2024-01-01"}],   # delivery_rows
            [],   # time_rows
        ]
        yield cursor

    def fake_recommend(history):
        call_count[0] += 1
        return {"recommendations": []}

    with patch("routes.challenge.db", mock_db_seq), \
         patch("routes.challenge.ai_challenge.recommend", fake_recommend):
        res = logged_in_client.get("/challenge")

    assert res.status_code == 200
    assert call_count[0] == 1, "TTL 만료 시 LLM 재호출 필요"


def test_avg_delivery_날짜_기반_산정():
    """delivery_rows의 실제 날짜 범위로 주 수를 산정한다."""
    from routes.challenge import _calc_avg_delivery_per_week

    # 14일(2주) 범위에 4건 → avg = 4 / 2 = 2.0
    base = datetime(2024, 1, 1)
    rows = [
        {"created_at": base},
        {"created_at": base + timedelta(days=3)},
        {"created_at": base + timedelta(days=7)},
        {"created_at": base + timedelta(days=13)},
    ]
    avg = _calc_avg_delivery_per_week(rows)
    assert pytest.approx(avg, rel=0.1) == pytest.approx(4 / (14 / 7), rel=0.1)


def test_avg_delivery_0건_엣지케이스():
    """0건이면 0.0을 반환하고 ZeroDivisionError가 발생하지 않는다."""
    from routes.challenge import _calc_avg_delivery_per_week

    assert _calc_avg_delivery_per_week([]) == 0.0


def test_avg_delivery_1건_엣지케이스():
    """1건이면 1.0을 반환한다 (주 수 = 1 보정)."""
    from routes.challenge import _calc_avg_delivery_per_week

    rows = [{"created_at": datetime(2024, 1, 5)}]
    assert _calc_avg_delivery_per_week(rows) == 1.0


def test_프롬프트_인젝션_truncate():
    """context 문자열 값이 200자를 초과하면 200자로 잘린다."""
    from ai.comment import _sanitize_context

    long_str = "A" * 300
    result = _sanitize_context({"key": long_str, "nested": {"inner": long_str}})
    assert len(result["key"]) == 200
    assert len(result["nested"]["inner"]) == 200


def test_프롬프트_인젝션_리스트_truncate():
    """list 안의 문자열 값도 200자로 잘린다."""
    from ai.comment import _sanitize_context

    result = _sanitize_context(["A" * 300, "B" * 50])
    assert len(result[0]) == 200
    assert len(result[1]) == 50  # 짧은 값은 유지


def test_CSRF_세션_토큰_없으면_빈_토큰_우회_차단(logged_in_client):
    """[P1] 세션에 CSRF 토큰이 없을 때 빈 X-CSRF-Token으로 요청하면 403을 반환한다."""
    challenge_id = "00000000-0000-0000-0000-000000000001"

    # 세션에 csrf_token 키 없음 (초기 상태)
    with logged_in_client.session_transaction() as sess:
        sess.pop("csrf_token", None)

    with patch("routes.challenge.db", _make_db_mock()):
        res = logged_in_client.post(
            f"/challenge/{challenge_id}/join",
            headers={"X-CSRF-Token": ""},  # 빈 토큰 — 우회 시도
        )

    assert res.status_code == 403, "세션 토큰 없을 때 빈 토큰은 403이어야 함"


def test_AI_추천_캐시_title_description_truncate(logged_in_client):
    """[P2] AI 추천 캐시 저장 시 title은 50자, description은 200자로 잘린다."""
    long_title = "T" * 100
    long_desc = "D" * 300

    with logged_in_client.session_transaction() as sess:
        sess.pop("ai_recommendations", None)
        sess.pop("ai_recommendations_ts", None)

    @contextmanager
    def mock_db_seq():
        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": "x"}
        cursor.fetchall.side_effect = [
            [],   # challenges
            [],   # user_challenges
            [{"created_at": "2024-01-01"}],   # delivery_rows
            [],   # time_rows
        ]
        yield cursor

    def fake_recommend(history):
        return {"recommendations": [{"title": long_title, "description": long_desc, "target_type": "delivery", "target_value": 2}]}

    with patch("routes.challenge.db", mock_db_seq), \
         patch("routes.challenge.ai_challenge.recommend", fake_recommend):
        res = logged_in_client.get("/challenge")

    assert res.status_code == 200
    with logged_in_client.session_transaction() as sess:
        cached = sess.get("ai_recommendations", [])
    assert len(cached) == 1
    assert len(cached[0]["title"]) == 50, "title은 50자로 잘려야 함"
    assert len(cached[0]["description"]) == 200, "description은 200자로 잘려야 함"


def test_sanitize_context_깊이_초과시_조기종료():
    """[P3] _sanitize_context는 depth > 10이면 str로 변환 후 200자로 자른다."""
    from ai.comment import _sanitize_context

    # depth 11에서 호출 — 조기 종료 경로
    result = _sanitize_context({"key": "val"}, _depth=11)
    assert isinstance(result, str)
    assert len(result) <= 200
