"""도파민 점수 + 랭킹 (담당: 김승현 — FR-26~31)."""
from flask import Blueprint, render_template, session, redirect, url_for
from routes.auth import login_required
from db.client import db
from datetime import timedelta
from utils.week import get_week_ranges, kst_bounds, kst_today
from services.score_service import recalculate_score  # Issue #58: services 계층으로 분리
from ai.comment import generate_tip

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

        # 4. 이번 달 주차별 트렌드 (1주차~N주차 고정 표시, 데이터 있는 주차만 막대 채움)
        today = kst_today()
        first_day = today.replace(day=1)
        # 다음 달 1일 기준으로 while 종료 — 월 경계에서 1일이 일요일인 경우도 정확히 처리
        if today.month == 12:
            next_month_first = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month_first = today.replace(month=today.month + 1, day=1)

        ws_cursor = first_day - timedelta(days=first_day.weekday())
        month_weeks = []
        while ws_cursor < next_month_first:
            month_weeks.append(ws_cursor.isoformat())
            ws_cursor += timedelta(weeks=1)

        if month_weeks:
            placeholders = ",".join(["%s"] * len(month_weeks))
            query = f"SELECT week_start, score FROM dopamine_scores WHERE user_id = %s AND week_start IN ({placeholders})"
            cursor.execute(query, [user_id] + month_weeks)
            score_map = {
                (r["week_start"].isoformat() if hasattr(r["week_start"], "isoformat") else str(r["week_start"])): r["score"]
                for r in (cursor.fetchall() or [])
            }
        else:
            score_map = {}

        weekly_scores = []
        for idx, ws_str in enumerate(month_weeks, start=1):
            sc = score_map.get(ws_str)
            weekly_scores.append({
                "day": f"{idx}주차",
                "score": sc,        # None = 기록 없음, 0 = 실제 0점으로 명확히 구분
                "has_data": sc is not None,
                "is_today": (ws_str == week_start),
            })

        # 5. 시간 통계 데이터 추출
        cursor.execute(
            """
            SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min
            FROM time_records
            WHERE user_id = %s AND created_at >= %s AND created_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        time_res = cursor.fetchone()
        avg_min = int(time_res["sum_min"] or 0) # 데이터가 없는 경우 0분 세팅
        avg_hours = avg_min // 60
        avg_remain_min = avg_min % 60
        avg_time_str = f"{avg_hours}시간 {avg_remain_min}분" if avg_hours > 0 else f"{avg_remain_min}분"

        # 이번 주 사용 시간의 25%를 잠금 해제 횟수로 환산 (기본 0회), UI 깨짐 방지를 위해 99회로 상한
        unlock_count = min(99, int(avg_min * 0.25))

        # 6. 배달 통계 데이터 추출
        cursor.execute(
            """
            SELECT SUM(total_price) as sum_price
            FROM delivery_records
            WHERE user_id = %s AND created_at >= %s AND created_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        delivery_res = cursor.fetchone()
        delivery_total = int(delivery_res["sum_price"] or 0)

        # 7. AI 맞춤 팁 생성
        tip = generate_tip(score, avg_min, delivery_total)

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
        unlock_count=unlock_count,
        tip=tip
    )
