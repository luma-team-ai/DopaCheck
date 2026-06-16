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


def test_챌린지_달성시_완료처리():
    """FR-37, FR-38: recalculate_score 호출 시 target 달성 챌린지 is_completed=1 갱신."""
    from services.score_service import recalculate_score

    cursor = MagicMock()
    # fetchone: delivery sum, time sum, delivery count, challenge count
    cursor.fetchone.side_effect = [
        {"sum_price": 20_000},
        {"sum_min": 0},
        {"cnt": 3},        # 배달 3회 — delivery target_value=2 초과 → 달성
        {"comp_count": 1},
    ]
    # 활성 챌린지: delivery 타입, target_value=2
    cursor.fetchall.return_value = [
        {"id": "uc-1", "target_type": "delivery", "target_value": 2}
    ]

    @contextmanager
    def _db():
        yield cursor

    with patch("services.score_service.db", _db):
        recalculate_score(user_id=1)

    # UPDATE user_challenges SET ... is_completed=1 호출 확인
    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE user_challenges" in str(c)]
    assert any("is_completed = 1" in c for c in update_calls), \
        "달성 시 is_completed=1 UPDATE가 호출돼야 함"


def test_time_챌린지_분단위_임계값_달성():
    """#60: time 챌린지 target_value(분) 기준으로 time_total_min >= tv 시 완료 처리."""
    from services.score_service import recalculate_score

    cursor = MagicMock()
    # fetchone: delivery sum=0, time sum=300분(5시간), delivery count=0, challenge count=1
    cursor.fetchone.side_effect = [
        {"sum_price": 0},
        {"sum_min": 300},   # 300분 — target_value=300과 일치 → 달성
        {"cnt": 0},
        {"comp_count": 1},
    ]
    # 활성 챌린지: time 타입, target_value=300(분)
    cursor.fetchall.return_value = [
        {"id": "uc-time-1", "target_type": "time", "target_value": 300}
    ]

    @contextmanager
    def _db():
        yield cursor

    with patch("services.score_service.db", _db):
        recalculate_score(user_id=1)

    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE user_challenges" in str(c)]
    assert any("is_completed = 1" in c for c in update_calls), \
        "time 챌린지: time_total_min(300) >= target_value(300) → is_completed=1 이어야 함"


def test_time_챌린지_분단위_미달성():
    """#60: time_total_min이 target_value 미만이면 미완료로 progress만 갱신."""
    from services.score_service import recalculate_score

    cursor = MagicMock()
    # fetchone: delivery sum=0, time sum=120분(2시간), delivery count=0, challenge count=0
    cursor.fetchone.side_effect = [
        {"sum_price": 0},
        {"sum_min": 120},   # 120분 < target_value=300 → 미달성
        {"cnt": 0},
        {"comp_count": 0},
    ]
    # 활성 챌린지: time 타입, target_value=300(분)
    cursor.fetchall.return_value = [
        {"id": "uc-time-2", "target_type": "time", "target_value": 300}
    ]

    @contextmanager
    def _db():
        yield cursor

    with patch("services.score_service.db", _db):
        recalculate_score(user_id=1)

    update_calls = [str(c) for c in cursor.execute.call_args_list if "UPDATE user_challenges" in str(c)]
    # is_completed=1 UPDATE가 없어야 함
    assert not any("is_completed = 1" in c for c in update_calls), \
        "time 챌린지: time_total_min(120) < target_value(300) → 완료 처리되면 안 됨"
    # 진행도 업데이트(is_completed 미변경)는 호출돼야 함
    assert any("UPDATE user_challenges" in c for c in update_calls), \
        "미달성 시에도 progress UPDATE는 호출돼야 함"


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
