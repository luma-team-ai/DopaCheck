# routes/home.py
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, url_for

from db.client import db
from routes.auth import login_required
from utils.week import get_week_ranges, kst_bounds

logger = logging.getLogger(__name__)

home_bp = Blueprint("home", __name__, url_prefix="/home")


@home_bp.route("")
@login_required
def index():
    """홈 대시보드 화면.
    
    1. 이번 주 도파민 점수 조회 및 랭킹 분위수 계산
    2. 이번 주 핵심 통계 집계: 배달 총액, SNS/게임 총 시간, 챌린지 현황
    3. 지난주 대비 도파민 점수 증감 비교 및 스마트 인사이트 제공
    """
    user_id = session.get("user_id")
    nickname = session.get("nickname", "사용자")

    # 1. 이번 주 및 지난 주 KST 기준 날짜 범위 계산
    this_week_range, last_week_range = get_week_ranges()
    this_start, this_end = this_week_range
    last_start, last_end = last_week_range

    # DB DATETIME 비교용 경계 구하기
    this_gte_at, this_lt_at = kst_bounds(this_start, this_end)

    # 점수 재계산 시도 (최신 점수 반영)
    try:
        from services.score_service import recalculate_score
        recalculate_score(user_id)
    except Exception as exc:
        logger.warning("도파민 점수 재계산 실패: %s", exc)

    with db() as cursor:
        # 2. 이번 주 도파민 점수 조회 (dopamine_scores)
        cursor.execute(
            """
            SELECT score, delivery_contribution, time_contribution, challenge_bonus 
            FROM dopamine_scores 
            WHERE user_id = %s AND week_start = %s
            """,
            (user_id, this_start)
        )
        score_record = cursor.fetchone()
        
        if not score_record:
            score_record = {
                "score": 0,
                "delivery_contribution": 0,
                "time_contribution": 0,
                "challenge_bonus": 0
            }
        
        score = score_record["score"]

        # 3. 랭킹 분위수 (percentile) 및 평균 점수 계산 (전체 유저 대비 상위 N%)
        cursor.execute("SELECT COUNT(*) as cnt FROM dopamine_scores WHERE week_start = %s", (this_start,))
        total_users = cursor.fetchone()["cnt"] or 1

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM dopamine_scores WHERE week_start = %s AND score > %s",
            (this_start, score)
        )
        higher_users = cursor.fetchone()["cnt"] or 0

        percentile = int((higher_users / total_users) * 100)
        if percentile == 0:
            percentile = 1  # 상위 0% 방지

        # 이번 주 전체 평균 점수 조회
        cursor.execute("SELECT AVG(score) as avg_score FROM dopamine_scores WHERE week_start = %s", (this_start,))
        avg_score_res = cursor.fetchone()
        avg_score_val = int(avg_score_res["avg_score"] or 0)
        avg_diff = score - avg_score_val

        # 4. 이번 주 핵심 통계 집계 (배달 금액, 사용 시간, 챌린지 달성 현황)
        # 4-1) 배달 총 지출액
        cursor.execute(
            """
            SELECT SUM(total_price) as sum_price 
            FROM delivery_records 
            WHERE user_id = %s AND created_at >= %s AND created_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        delivery_sum = cursor.fetchone()
        delivery_total = delivery_sum["sum_price"] or 0

        # 4-2) SNS + 게임 사용 시간
        cursor.execute(
            """
            SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min 
            FROM time_records 
            WHERE user_id = %s AND created_at >= %s AND created_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        time_sum = cursor.fetchone()
        time_total_min = time_sum["sum_min"] or 0
        
        # 시간 형식 포맷팅 (예: 14h 30m 또는 45m)
        hours = time_total_min // 60
        mins = time_total_min % 60
        if hours > 0:
            time_str = f"{hours}h {mins}m"
        else:
            time_str = f"{mins}m"

        # 4-3) 챌린지 달성 현황 (완료 기준 score_service와 일치 — Issue #69)
        # 이번 주에 시작했거나 이번 주에 완료된 챌린지 수 (합집합: 완료가 항상 분모에 포함)
        cursor.execute(
            """
            SELECT COUNT(*) as total_cnt
            FROM user_challenges
            WHERE user_id = %s AND (
              (started_at >= %s AND started_at < %s)
              OR (is_completed = 1 AND completed_at >= %s AND completed_at < %s)
            )
            """,
            (user_id, this_gte_at, this_lt_at, this_gte_at, this_lt_at)
        )
        total_challenges = cursor.fetchone()["total_cnt"] or 0

        # 이번 주에 완료된 챌린지 수 (completed_at 기준 — score_service와 동일)
        cursor.execute(
            """
            SELECT COUNT(*) as comp_cnt
            FROM user_challenges
            WHERE user_id = %s AND is_completed = 1 AND completed_at >= %s AND completed_at < %s
            """,
            (user_id, this_gte_at, this_lt_at)
        )
        completed_challenges = cursor.fetchone()["comp_cnt"] or 0

        # 5. 지난주 점수 비교를 통한 스마트 인사이트 문구 생성
        cursor.execute(
            "SELECT score FROM dopamine_scores WHERE user_id = %s AND week_start = %s",
            (user_id, last_start)
        )
        last_score_record = cursor.fetchone()
        
        if last_score_record:
            last_score = last_score_record["score"]
            diff = score - last_score
            if diff > 0:
                insight_title = f"도파민 점수가 지난 주보다 {diff}점 높아졌어요. 주의하세요!"
            elif diff < 0:
                insight_title = f"도파민 점수가 지난 주보다 {abs(diff)}점 낮아졌어요. 잘 하고 있어요!"
            else:
                insight_title = "도파민 수치가 지난 주와 동일하게 유지되고 있어요."
        else:
            insight_title = "첫 도파민 분석 주간입니다! 건강하게 도파민을 관리해 보세요. 🌱"

    return render_template(
        "home.html",
        nickname=nickname,
        score=score,
        percentile=percentile,
        avg_diff=avg_diff,
        delivery_total=delivery_total,
        time_str=time_str,
        completed_challenges=completed_challenges,
        total_challenges=total_challenges,
        insight_title=insight_title
    )
