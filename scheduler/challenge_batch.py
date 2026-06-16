"""지난 주 미판정 챌린지 일괄 달성 판정 — 월요일 00:01 KST 배치 (P1-B #194).

recalculate_score 는 이벤트 기반이라 사용자가 일요일에 앱을 안 열면
목표를 달성해도 완료 처리가 되지 않는다. 이 배치가 월요일 새벽에 보정한다.

멱등성: UPDATE WHERE is_completed = 0 이므로 gunicorn 멀티워커가 동시에 실행해도
두 번째 실행은 업데이트 대상이 없어 안전하다.
"""
import logging
from datetime import datetime as _dt

from db.client import db
from utils.week import get_week_ranges, kst_bounds

logger = logging.getLogger(__name__)


def settle_last_week_challenges() -> int:
    """지난 주 종료 후 미판정 상태로 남은 챌린지를 일괄 달성 판정한다.

    Returns:
        완료 처리된 user_challenges 행 수.
    """
    _, last_week = get_week_ranges()
    week_start, week_end = last_week
    gte_at, lt_at = kst_bounds(week_start, week_end)

    completed_count = 0
    with db() as cursor:
        cursor.execute(
            "SELECT uc.id, uc.user_id, uc.started_at, c.target_type, c.target_value"
            " FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id"
            " WHERE uc.is_completed = 0 AND uc.started_at < %s",
            (lt_at,),
        )
        pending = cursor.fetchall() or []

        for ch in pending:
            tt = ch["target_type"]
            tv = ch["target_value"] or 1
            user_id = ch["user_id"]

            # 참여 시점(started_at)과 주 시작 중 늦은 쪽부터 집계 — score_service와 동일 로직
            ch_started_at = ch["started_at"]
            if ch_started_at:
                gte_dt = _dt.fromisoformat(gte_at)
                started_dt = (
                    ch_started_at if isinstance(ch_started_at, _dt)
                    else _dt.fromisoformat(str(ch_started_at))
                )
                ch_gte = max(gte_dt, started_dt).strftime("%Y-%m-%d %H:%M:%S")
            else:
                ch_gte = gte_at

            cursor.execute(
                "SELECT COUNT(*) as cnt FROM delivery_records"
                " WHERE user_id = %s AND created_at >= %s AND created_at < %s",
                (user_id, ch_gte, lt_at),
            )
            delivery_count = cursor.fetchone()["cnt"] or 0

            cursor.execute(
                "SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min"
                " FROM time_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
                (user_id, ch_gte, lt_at),
            )
            time_total_min = cursor.fetchone()["sum_min"] or 0
            time_hours = time_total_min / 60

            if tt == "delivery":
                done = delivery_count < tv
            elif tt == "time":
                done = time_total_min < tv
            else:  # "both"
                done = delivery_count < tv and time_hours < tv

            if done:
                cursor.execute(
                    "UPDATE user_challenges"
                    " SET progress = %s, is_completed = 1, completed_at = %s"
                    " WHERE id = %s AND is_completed = 0",
                    (tv, f"{week_end} 23:59:59", ch["id"]),
                )
                completed_count += 1

    logger.info("지난 주 챌린지 배치 완료: %d건 달성 처리", completed_count)
    return completed_count
