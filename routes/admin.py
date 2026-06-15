# routes/admin.py
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash

from db.client import db
from routes.auth import login_required
from utils.week import kst_today

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    """관리자 권한을 강제하는 데코레이터.
    
    비관리자(role != 'admin') 접근 시 에러 노출 없이 홈('/')으로 리다이렉트합니다. (FR-54)
    """
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        role = session.get("role")
        
        # 세션에 역할이 없는 경우 DB에서 최신 역할을 조회하여 갱신합니다.
        if not role:
            with db() as cursor:
                cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                role = user["role"] if user else "user"
                session["role"] = role
        
        if role != "admin":
            return redirect(url_for("home.index"))
            
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("")
@admin_required
def admin_dashboard():
    """관리자 통계 대시보드 화면. (FR-55~58)"""
    
    # 7일 전(KST) 구하기 (활성 사용자 집계용)
    seven_days_ago = kst_today() - timedelta(days=7)
    # DB DATETIME과 비교하기 위해 포맷팅
    active_date_limit = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")

    with db() as cursor:
        # 1. 사용자 현황 (FR-55)
        # 1-1) 전체 가입자 수
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"] or 0

        # 1-2) 활성 사용자 수 (최근 7일 내 분석 기록이 있는 사용자)
        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id) as cnt
            FROM (
                SELECT user_id FROM delivery_records WHERE created_at >= %s
                UNION ALL
                SELECT user_id FROM time_records WHERE created_at >= %s
            ) as active_users
            """,
            (active_date_limit, active_date_limit)
        )
        active_users = cursor.fetchone()["cnt"] or 0

        # 2. 분석 통계 (FR-56)
        # 2-1) 배달 분석 건수
        cursor.execute("SELECT COUNT(*) as cnt FROM delivery_records")
        delivery_count = cursor.fetchone()["cnt"] or 0

        # 2-2) 시간 분석 건수
        cursor.execute("SELECT COUNT(*) as cnt FROM time_records")
        time_count = cursor.fetchone()["cnt"] or 0

        # 2-3) 총 배달 지출 금액
        cursor.execute("SELECT SUM(total_price) as sum_price FROM delivery_records")
        total_price = cursor.fetchone()["sum_price"] or 0

        # 2-4) 총 사용 시간 (분 단위를 시간 단위로 환산)
        cursor.execute("SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min FROM time_records")
        total_min_res = cursor.fetchone()
        total_min = total_min_res["sum_min"] or 0
        total_hours = total_min // 60

        # 3. 도파민 점수 분포 (FR-57)
        cursor.execute(
            """
            SELECT 
                AVG(score) as avg_score,
                MAX(score) as max_score,
                MIN(score) as min_score
            FROM dopamine_scores
            """
        )
        score_stats = cursor.fetchone()
        avg_score = int(score_stats["avg_score"] or 0)
        max_score = score_stats["max_score"] or 0
        min_score = score_stats["min_score"] or 0

        # 점수 구간별 분포
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN score BETWEEN 0 AND 20 THEN 1 ELSE 0 END) as g1,
                SUM(CASE WHEN score BETWEEN 21 AND 40 THEN 1 ELSE 0 END) as g2,
                SUM(CASE WHEN score BETWEEN 41 AND 60 THEN 1 ELSE 0 END) as g3,
                SUM(CASE WHEN score BETWEEN 61 AND 80 THEN 1 ELSE 0 END) as g4,
                SUM(CASE WHEN score BETWEEN 81 AND 100 THEN 1 ELSE 0 END) as g5
            FROM dopamine_scores
            """
        )
        distribution = cursor.fetchone()
        g1 = distribution["g1"] or 0
        g2 = distribution["g2"] or 0
        g3 = distribution["g3"] or 0
        g4 = distribution["g4"] or 0
        g5 = distribution["g5"] or 0

        # 막대 그래프 높이 동적 계산 (가장 많은 구간을 90% 높이로 기준으로 삼음)
        max_cnt = max(g1, g2, g3, g4, g5, 1)
        h1 = int(g1 / max_cnt * 90)
        h2 = int(g2 / max_cnt * 90)
        h3 = int(g3 / max_cnt * 90)
        h4 = int(g4 / max_cnt * 90)
        h5 = int(g5 / max_cnt * 90)
        
        # 최저 높이 방어 (0이 아니면 최소 5%는 보이도록)
        h1 = max(5, h1) if g1 > 0 else 0
        h2 = max(5, h2) if g2 > 0 else 0
        h3 = max(5, h3) if g3 > 0 else 0
        h4 = max(5, h4) if g4 > 0 else 0
        h5 = max(5, h5) if g5 > 0 else 0

        # 4. 점수 랭킹 TOP 5 (FR-57)
        # 사용자별 역대 최고 점수를 기준으로 상위 5명을 뽑아옵니다.
        cursor.execute(
            """
            SELECT u.nickname, MAX(d.score) as top_score, u.email
            FROM dopamine_scores d
            JOIN users u ON d.user_id = u.id
            GROUP BY d.user_id, u.nickname, u.email
            ORDER BY top_score DESC
            LIMIT 5
            """
        )
        ranking_list = cursor.fetchall()

        # 5. 챌린지 통계 (FR-58)
        cursor.execute("SELECT COUNT(*) as total FROM user_challenges")
        challenge_total = cursor.fetchone()["total"] or 0

        cursor.execute("SELECT COUNT(*) as completed FROM user_challenges WHERE is_completed = 1")
        challenge_completed = cursor.fetchone()["completed"] or 0

        if challenge_total > 0:
            completion_rate = int(challenge_completed / challenge_total * 100)
        else:
            completion_rate = 0
            
        # 도넛 차트 SVG stroke-dashoffset 계산 (dasharray = 282.7)
        dashoffset = float(282.7 * (1 - completion_rate / 100))

    return render_template(
        "admin/index.html",
        total_users=total_users,
        active_users=active_users,
        delivery_count=delivery_count,
        time_count=time_count,
        total_price=total_price,
        total_hours=total_hours,
        avg_score=avg_score,
        max_score=max_score,
        min_score=min_score,
        h1=h1, h2=h2, h3=h3, h4=h4, h5=h5,
        g1=g1, g2=g2, g3=g3, g4=g4, g5=g5,
        ranking_list=ranking_list,
        challenge_total=challenge_total,
        challenge_completed=challenge_completed,
        completion_rate=completion_rate,
        dashoffset=dashoffset
    )
