"""도파민 점수 + 랭킹 (담당: 김승현 — FR-26~31)."""
from flask import Blueprint, render_template, session, redirect, url_for
from routes.auth import login_required
from db.client import db
from utils.week import get_week_ranges, kst_bounds, kst_today

score_bp = Blueprint("score", __name__, url_prefix="/score")


@score_bp.route("")
@login_required
def score_page():
    """도파민 점수 페이지.

    1. dopamine_scores에서 이번 주 점수 조회 (FR-26)
    2. 항목별 기여도 시각화 데이터 (FR-28)
    3. 전체 사용자 평균 대비 내 점수 (FR-29)
    4. 상위 N% 랭킹 — 시드 더미 데이터 20건 전제 (FR-30)
    """
    user_id = session.get("user_id")
    this_week_range, last_week_range = get_week_ranges()
    week_start, week_end = this_week_range
    last_week_start, _ = last_week_range
    this_gte_at, this_lt_at = kst_bounds(week_start, week_end)

    # 점수 재산출 트리거 (데이터가 없거나 최신화가 필요할 때 대비)
    try:
        recalculate_score(user_id)
    except Exception:
        pass

    with db() as cursor:
        # 1. 이번 주 점수 및 기여도 데이터 가져오기
        cursor.execute(
            """
            SELECT score, delivery_contribution, time_contribution, challenge_bonus 
            FROM dopamine_scores 
            WHERE user_id = %s AND week_start = %s
            """,
            (user_id, week_start)
        )
        score_record = cursor.fetchone()

        if not score_record:
            # 방어용 기본값 (첫 로그인 후 분석 기록이 전혀 없는 경우 0점 세팅)
            score_record = {
                "score": 0,
                "delivery_contribution": 0,
                "time_contribution": 0,
                "challenge_bonus": 0
            }

        score = score_record["score"]

        # 2. 랭킹 분위수 (percentile) 산출 (FR-30)
        # 전체 유저 수 집계 (동일 주차)
        cursor.execute("SELECT COUNT(*) as cnt FROM dopamine_scores WHERE week_start = %s", (week_start,))
        total_users = cursor.fetchone()["cnt"] or 1

        # 나보다 점수가 높은 유저 수 집계
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM dopamine_scores WHERE week_start = %s AND score > %s",
            (week_start, score)
        )
        higher_users = cursor.fetchone()["cnt"] or 0

        percentile = int((higher_users / total_users) * 100)
        if percentile == 0:
            percentile = 1 # 최소 상위 1% 방지

        # 3. 지난주 점수 비교 (점수 차이 산출, 단위=점)
        cursor.execute(
            "SELECT score FROM dopamine_scores WHERE user_id = %s AND week_start = %s",
            (user_id, last_week_start)
        )
        last_week_record = cursor.fetchone()
        if last_week_record:
            last_score = last_week_record["score"]
            diff = score - last_score
            if diff >= 0:
                compare_last_week = f"지난주보다 {diff}점 상승했습니다."
            else:
                compare_last_week = f"지난주보다 {abs(diff)}점 하락했습니다."
        else:
            compare_last_week = "첫 점수 분석 주간입니다! 지표가 순조롭게 분석되고 있습니다."

        # 4. 최근 7일(월~일) 요일별 트렌드 — 일별 점수 기록이 없으므로
        #    오늘(score)만 채우고, 그 외 요일은 None(데이터 없음)으로 공백 처리한다.
        days_names = ["월", "화", "수", "목", "금", "토", "일"]
        weekly_scores = []
        current_weekday = kst_today().weekday()

        for idx in range(7):
            day_score = score if idx == current_weekday else None
            weekly_scores.append({
                "day": days_names[idx],
                "score": day_score,
                "is_today": (idx == current_weekday)
            })

        # 5. 시간 통계 데이터 추출
        cursor.execute(
            """
            SELECT AVG(youtube_min + instagram_min + tiktok_min) as avg_min
            FROM time_records
            WHERE user_id = %s AND created_at >= %s AND created_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        avg_res = cursor.fetchone()
        avg_min = int(avg_res["avg_min"] or 0) # 데이터가 없는 경우 0분 세팅
        avg_hours = avg_min // 60
        avg_remain_min = avg_min % 60
        avg_time_str = f"{avg_hours}시간 {avg_remain_min}분" if avg_hours > 0 else f"{avg_remain_min}분"

        # 평균 사용 시간의 25%를 잠금 해제 횟수로 환산 (기본 0회), UI 깨짐 방지를 위해 99회로 상한
        unlock_count = min(99, int(avg_min * 0.25))

    return render_template(
        "score/index.html",
        score=score,
        delivery_contribution=score_record["delivery_contribution"],
        time_contribution=score_record["time_contribution"],
        challenge_bonus=score_record["challenge_bonus"],
        percentile=percentile,
        compare_last_week=compare_last_week,
        weekly_scores=weekly_scores,
        avg_time_str=avg_time_str,
        unlock_count=unlock_count
    )


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
        delivery_sum = cursor.fetchone()
        delivery_total = delivery_sum["sum_price"] or 0

        # 이번 주 시간 소비 총합 집계
        cursor.execute(
            "SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min FROM time_records WHERE user_id = %s AND created_at >= %s AND created_at < %s",
            (user_id, gte_at, lt_at)
        )
        time_sum = cursor.fetchone()
        time_total_min = time_sum["sum_min"] or 0

        # 이번 주 완료한 챌린지 수 집계
        cursor.execute(
            "SELECT COUNT(*) as comp_count FROM user_challenges WHERE user_id = %s AND is_completed = 1 AND completed_at >= %s AND completed_at < %s",
            (user_id, gte_at, lt_at)
        )
        challenge_sum = cursor.fetchone()
        challenge_completed = challenge_sum["comp_count"] or 0

        # 공식 대입 계산
        # 1) 배달 지출 점수 (40점 만점): 기본 40점, 5000원 지출당 3점 감점 (최소 0)
        delivery_score = max(0, 40 - int(delivery_total / 5000) * 3)

        # 2) 시간 소비 점수 (40점 만점): 기본 40점, 사용 시간 1시간당 5점 감점 (최소 0)
        time_score = max(0, 40 - int(time_total_min / 60) * 5)

        # 3) 챌린지 보너스 (20점 만점): 개당 +5점 가산 (최대 20점)
        challenge_score = min(20, challenge_completed * 5)

        # 최종 스코어 합산
        total_score = delivery_score + time_score + challenge_score

        # DB에 upsert 저장
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
            (user_id, total_score, delivery_score, time_score, challenge_score, week_start)
        )

