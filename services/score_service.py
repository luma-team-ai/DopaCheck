"""점수 재산출 서비스 — 라우트 계층에서 분리 (Issue #58)."""
import logging

import ai.score as ai_score
from db.client import db
from utils.week import get_week_ranges, kst_bounds

logger = logging.getLogger(__name__)


def recalculate_score(user_id: int) -> None:
    """분석 결과 저장 시 호출되는 점수 재산출 공통 함수. (FR-31)

    delivery/time/challenge 라우트에서 저장 직후 호출한다.
    1. 이번 주 배달·시간·챌린지 데이터 집계
    2. dopamine_scores (user_id, week_start) upsert
    """
    this_week_range, _ = get_week_ranges()
    week_start, week_end = this_week_range
    gte_at, lt_at = kst_bounds(week_start, week_end)

    with db() as cursor:
        # 이번 주 배달 소비 총액 집계
        cursor.execute(
            "SELECT SUM(total_price) as sum_price FROM delivery_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
            (user_id, gte_at, lt_at)
        )
        delivery_total = cursor.fetchone()["sum_price"] or 0

        # 이번 주 시간 소비 총합 집계
        cursor.execute(
            "SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min FROM time_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
            (user_id, gte_at, lt_at)
        )
        time_total_min = cursor.fetchone()["sum_min"] or 0

        # 이번 주 배달 횟수 (챌린지 progress용 — 소비금액이 아닌 건수)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM delivery_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
            (user_id, gte_at, lt_at)
        )
        delivery_count = cursor.fetchone()["cnt"] or 0

        # ── 챌린지 진행도 갱신 + 달성 판정 (FR-36~38, #73) ─────────────────────────
        cursor.execute(
            "SELECT uc.id, c.target_type, c.target_value"
            " FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id"
            " WHERE uc.user_id = %s AND uc.is_completed = 0",
            (user_id,)
        )
        active_challenges = cursor.fetchall() or []
        time_hours = time_total_min / 60

        for ch in active_challenges:
            tt = ch["target_type"]
            tv = ch["target_value"] or 1
            if tt == "delivery":
                progress = delivery_count
                # "N회 이하" 챌린지: 목표 횟수(tv)에 딱 도달했을 때 완료
                # (>= 로 초과 시에도 완료 처리되던 버그 수정)
                done = delivery_count == tv
            elif tt == "time":
                # target_value 단위는 분(min) — time_hours(시간)와 단위 불일치 버그 수정
                progress = time_total_min
                done = time_total_min == tv
            else:  # "both"
                # target_value=3 은 배달 횟수 기준; SNS 시간 목표는 별도 컬럼 없음(스키마 개선 필요)
                # 현재는 배달 횟수 기준으로만 완료 판정
                progress = delivery_count
                done = delivery_count == tv

            if done:
                cursor.execute(
                    "UPDATE user_challenges"
                    " SET progress = %s, is_completed = 1, completed_at = NOW()"
                    " WHERE id = %s AND is_completed = 0",
                    (tv, ch["id"])
                )
            else:
                cursor.execute(
                    "UPDATE user_challenges SET progress = %s WHERE id = %s AND is_completed = 0",
                    (progress, ch["id"])
                )

        # 이번 주 완료한 챌린지 수 집계 (진행도 갱신 후)
        cursor.execute(
            "SELECT COUNT(*) as comp_count FROM user_challenges WHERE user_id = %s AND is_completed = 1 AND completed_at >= %s AND completed_at < %s",
            (user_id, gte_at, lt_at)
        )
        challenge_completed = cursor.fetchone()["comp_count"] or 0

        # 공식 대입 계산 — #48 합의 계산식(config.py 상수 + ai.score.calculate) 사용
        result = ai_score.calculate({
            "delivery_total": delivery_total,
            "time_total_min": time_total_min,
            "challenge_completed": challenge_completed,
        })

        # DB에 upsert 저장 (id는 스키마 DEFAULT (UUID())로 생성)
        cursor.execute(
            """
            INSERT INTO dopamine_scores (user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                score = VALUES(score),
                delivery_contribution = VALUES(delivery_contribution),
                time_contribution = VALUES(time_contribution),
                challenge_bonus = VALUES(challenge_bonus)
            """,
            (user_id, result["score"], result["delivery_contribution"],
             result["time_contribution"], result["challenge_bonus"], week_start)
        )

        logger.info("점수 재산출 완료: user_id=%s, score=%s", user_id, result["score"])
