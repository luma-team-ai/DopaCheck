"""점수 재산출 서비스 — 라우트 계층에서 분리 (Issue #58)."""
import logging
from datetime import date, datetime, timedelta

import ai.score as ai_score
from db.client import db
from utils.week import get_week_ranges, kst_bounds, kst_today, week_bounds

logger = logging.getLogger(__name__)


def _aggregate_counts(cursor, user_id: int, gte_at: str, lt_at: str) -> tuple[int, int]:
    """주어진 [gte_at, lt_at) 경계로 배달 횟수·시간 총합(분)을 집계한다.

    챌린지 완료 판정 전용 — '완전히 끝난 주'(judge_week)의 카운트를 따로 계산할 때 쓴다.
    점수 계산용 집계(이번 주)와 단위·경계 패턴을 동일하게 유지한다.

    Returns:
        (delivery_count, time_total_min)
    """
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM delivery_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
        (user_id, gte_at, lt_at)
    )
    delivery_count = cursor.fetchone()["cnt"] or 0

    cursor.execute(
        "SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min FROM time_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
        (user_id, gte_at, lt_at)
    )
    time_total_min = cursor.fetchone()["sum_min"] or 0

    return delivery_count, time_total_min


def recalculate_score(user_id: int) -> None:
    """분석 결과 저장 시 호출되는 점수 재산출 공통 함수. (FR-31)

    delivery/time/challenge 라우트에서 저장 직후 호출한다.
    1. 이번 주 배달·시간·챌린지 데이터 집계 (점수 계산용)
    2. '완전히 끝난 주'(judge_week) 기준 챌린지 완료 판정
    3. dopamine_scores (user_id, week_start) upsert
    """
    this_week_range, last_week_range = get_week_ranges()
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
            "SELECT uc.id, uc.started_at, c.target_type, c.target_value"
            " FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id"
            " WHERE uc.user_id = %s AND uc.is_completed = 0",
            (user_id,)
        )
        active_challenges = cursor.fetchall() or []

        # progress(목록 화면 표시값)는 '이번 주' 기준으로 별도 계산한다 (#194 P1-2).
        # 완료 판정(done)만 judge_week(완전히 끝난 주)를 쓰고, 표시값까지 judge_week를
        # 쓰면 월~토에 지난주 숫자가 보이고 일요일에 점프하는 문제가 생기므로 분리한다.
        time_hours = time_total_min / 60  # 이번 주 시간 총합(시) — both progress용

        # ── 챌린지 완료 판정은 '완전히 끝난 주'(judge_week) 기준 ──────────────────
        # 호출이 전부 이벤트 기반(스케줄러 없음)이라, 사용자가 일요일에 앱을 안 열면
        # 목표를 달성해도 영영 미완료가 되는 문제(#194 P1-B)를 막는다.
        #   - 오늘이 일요일(이번 주 종료일)이면 → 이번 주 데이터로 판정.
        #   - 오늘이 월~토면 → 지난주(완전히 끝난 주) 데이터로 판정.
        # 점수 계산용 집계(delivery_total/time_total_min/delivery_count)는 그대로
        # '이번 주' 기준을 유지하고, 판정용 카운트만 judge_week 기준으로 분리한다.
        # judge 집계 2건은 활성 챌린지가 있을 때만 실행한다 — 비참여자에게 불필요한
        # DB 쿼리가 매 페이지 진입마다 나가던 문제(#194 P2)를 막는다.
        # DopaCheck 챌린지는 전부 '줄이기' 방향 — 목표값 미만이어야 달성 (< tv).
        # "한도 N번" 표시 시 N번을 달성하면 실패, N-1번 이하여야 성공.
        #
        # judge_* 선초기화(#203 봇 P1) — 이 변수들은 아래 for 루프 안에서만 참조되고,
        # 루프와 if 블록이 동일하게 active_challenges에 게이트되므로 빈 리스트에선 둘 다
        # 실행되지 않아 실제 NameError는 없다. 그래도 빈 경로 NameError를 원천 차단한다.
        # judge_start 기본값은 먼 미래("9999-12-31")로 둬, 혹시 참조돼도 가입주차 비교가
        # False가 되어 '판정 skip'(fail-safe, 오완료 아님)으로 흐르게 한다.
        judge_start = "9999-12-31"
        judge_delivery_count = judge_time_total_min = 0
        judge_time_hours = 0.0
        if active_challenges:
            week_end_date = date.fromisoformat(week_end)
            if kst_today() >= week_end_date:
                judge_start, judge_end = week_start, week_end
            else:
                judge_start, judge_end = last_week_range
            judge_gte, judge_lt = kst_bounds(judge_start, judge_end)
            judge_delivery_count, judge_time_total_min = _aggregate_counts(
                cursor, user_id, judge_gte, judge_lt
            )
            judge_time_hours = judge_time_total_min / 60

        for ch in active_challenges:
            # ── 가입 주차 필터 (#194 P1-1) ──────────────────────────────────────
            # judge_week가 이 챌린지의 가입 주(started_at이 속한 주)보다 이전이면,
            # 그 주엔 아직 참여하지 않았으므로 완료 판정에서 제외한다. 미적용 시
            # judge_week=지난주 + judge 0건이면 줄이기형 '0 < tv'가 참이 되어
            # 이번 주에 새로 참여한 챌린지가 지난주 데이터로 즉시 완료되는 버그 발생.
            started_at = ch["started_at"]
            if started_at is None:
                continue  # started_at은 NOT NULL이나 방어적으로 가드 (#194 봇 리뷰)
            # DATETIME 컬럼은 pymysql DictCursor가 datetime으로 반환 — .date()로 정규화.
            # (혹시 date로 들어오는 경우도 방어적으로 처리)
            joined_date = started_at.date() if isinstance(started_at, datetime) else started_at
            joined_week_start = week_bounds(joined_date)[0]
            if judge_start < joined_week_start:
                # judge_week(ISO 문자열) < 가입 주 시작(ISO 문자열) — 사전식=시간순 비교.
                continue

            tt = ch["target_type"]
            tv = ch["target_value"] or 1
            if tt == "delivery":
                # progress=이번 주 표시값, done=judge_week 기준 (#194 P1-2)
                # 한도 tv번 초과 없이 마쳐야 달성 — tv번 사용 시 실패 (엄격 미만 < tv)
                progress = delivery_count
                done = judge_delivery_count < tv
            elif tt == "time":
                # target_value 단위: 분(min). progress=이번 주, done=judge_week.
                progress = time_total_min
                done = judge_time_total_min < tv
            else:  # "both"
                # target_value 단위: 배달은 횟수, 시간은 시(hour) — seed.sql "3시간 이하" 참고.
                # progress=이번 주 값, done=judge_week 값.
                # float 비교 유지 — int() 절삭 시 3.1h → 3h < 3 = False 가 되어 미달성 오판 방지.
                progress = min(delivery_count, int(time_hours))
                done = judge_delivery_count < tv and judge_time_hours < tv

            if done:
                # 주의(#194 P2): judge_week=지난주 완료 시 completed_at=NOW()(이번 주)라
                # 지난주 달성이 이번 주 challenge_completed(보너스)에 산입됨 — 후속 검토(#194 P2).
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


def backfill_all_scores() -> int:
    """점수 공식 반전(#175) 후 과거 dopamine_scores 전체를 새 공식으로 재계산한다.

    dopamine_scores의 모든 (user_id, week_start) 행을 원본 기록에서 재집계해
    score / delivery_contribution / time_contribution / challenge_bonus 를 UPDATE한다.

    - 챌린지 테이블(user_challenges)은 SELECT만 수행 — 진행도·완료 상태 변경 없음.
    - 멱등성 보장: 같은 원본 데이터에 대해 몇 번 실행해도 동일한 결과.

    Returns:
        갱신한 dopamine_scores 행 수.
    """
    logger.info("백필 시작: dopamine_scores 전체 행 재계산")

    with db() as cursor:
        # 1. 모든 (user_id, week_start) 조합 수집
        cursor.execute("SELECT DISTINCT user_id, week_start FROM dopamine_scores")
        rows = cursor.fetchall() or []

        updated = 0
        for row in rows:
            user_id = row["user_id"]
            week_start = row["week_start"]

            # week_start를 ISO 문자열로 정규화 (DB 드라이버가 date 객체로 반환할 수 있음)
            ws = week_start if isinstance(week_start, str) else week_start.isoformat()
            week_end_iso = (date.fromisoformat(ws) + timedelta(days=6)).isoformat()
            gte_at, lt_at = kst_bounds(ws, week_end_iso)

            # 배달 총액 집계
            cursor.execute(
                "SELECT SUM(total_price) AS sum_price FROM delivery_records"
                " WHERE user_id=%s AND created_at>=%s AND created_at<%s",
                (user_id, gte_at, lt_at),
            )
            delivery_total = cursor.fetchone()["sum_price"] or 0

            # 시간 총합 집계
            cursor.execute(
                "SELECT SUM(youtube_min+instagram_min+tiktok_min+game_min) AS sum_min"
                " FROM time_records WHERE user_id=%s AND created_at>=%s AND created_at<%s",
                (user_id, gte_at, lt_at),
            )
            time_total_min = cursor.fetchone()["sum_min"] or 0

            # 챌린지 완료 수 집계 (SELECT만 — 상태 변경 없음)
            cursor.execute(
                "SELECT COUNT(*) AS comp_count FROM user_challenges"
                " WHERE user_id=%s AND is_completed=1 AND completed_at>=%s AND completed_at<%s",
                (user_id, gte_at, lt_at),
            )
            challenge_completed = cursor.fetchone()["comp_count"] or 0

            # 새 공식으로 재계산
            result = ai_score.calculate({
                "delivery_total": delivery_total,
                "time_total_min": time_total_min,
                "challenge_completed": challenge_completed,
            })

            # 해당 행 UPDATE
            cursor.execute(
                "UPDATE dopamine_scores"
                " SET score=%s, delivery_contribution=%s, time_contribution=%s, challenge_bonus=%s"
                " WHERE user_id=%s AND week_start=%s",
                (
                    result["score"],
                    result["delivery_contribution"],
                    result["time_contribution"],
                    result["challenge_bonus"],
                    user_id,
                    ws,
                ),
            )
            updated += 1

    logger.info("백필 완료: %d개 행 재계산", updated)
    return updated
