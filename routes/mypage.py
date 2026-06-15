# routes/mypage.py
import logging
from flask import Blueprint, render_template, session, redirect, url_for, request, flash

from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf
from utils.week import get_week_ranges

MAX_HOURLY_WAGE = 1_000_000

logger = logging.getLogger(__name__)

mypage_bp = Blueprint("mypage", __name__, url_prefix="/mypage")


@mypage_bp.route("")
@login_required
def mypage_page():
    """마이페이지 화면 조회."""
    user_id = session.get("user_id")
    
    # 이번 주 KST 기준 날짜 범위 계산
    this_week_range, _ = get_week_ranges()
    this_start, _ = this_week_range

    with db() as cursor:
        # 1. 사용자 정보 조회 (닉네임, 이메일, 가입일, 시급)
        cursor.execute(
            "SELECT nickname, email, created_at, hourly_wage FROM users WHERE id = %s",
            (user_id,)
        )
        user_info = cursor.fetchone()
        
        if not user_info:
            flash("사용자 정보를 찾을 수 없습니다.", "error")
            return redirect(url_for("home.index"))

        # 가입일 포맷팅
        created_at_dt = user_info["created_at"]
        if created_at_dt:
            joined_date_str = created_at_dt.strftime("%Y년 %m월 %d일")
        else:
            joined_date_str = "알 수 없음"

        # 이메일 전처리 (카카오 소셜 사용자의 경우 kakao_xxx 로 표시되므로 이메일 형태가 아니면 표기 수정)
        email_display = user_info["email"]
        if email_display.startswith("kakao_"):
            email_display = "카카오 소셜 회원"

        # 2. 이번 주 도파민 점수 조회
        cursor.execute(
            "SELECT score FROM dopamine_scores WHERE user_id = %s AND week_start = %s",
            (user_id, this_start)
        )
        score_record = cursor.fetchone()
        score = score_record["score"] if score_record else 0

        # 3. 완료된 챌린지 수 조회
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM user_challenges WHERE user_id = %s AND is_completed = 1",
            (user_id,)
        )
        completed_challenges = cursor.fetchone()["cnt"] or 0

        # 4. 총 분석 횟수 조회 (배달 영수증 분석 횟수 + 시간 소비 분석 횟수)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM delivery_records WHERE user_id = %s",
            (user_id,)
        )
        delivery_cnt = cursor.fetchone()["cnt"] or 0

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM time_records WHERE user_id = %s",
            (user_id,)
        )
        time_cnt = cursor.fetchone()["cnt"] or 0
        
        total_analyses = delivery_cnt + time_cnt

    return render_template(
        "mypage/mypage.html",
        user=user_info,
        joined_date_str=joined_date_str,
        email_display=email_display,
        score=score,
        completed_challenges=completed_challenges,
        total_analyses=total_analyses,
        csrf_token=get_or_create_csrf_token()
    )


@mypage_bp.route("/update_wage", methods=["POST"])
@login_required
def update_wage():
    """사용자의 기본 시급 설정을 업데이트."""
    verify_csrf()

    user_id = session.get("user_id")
    hourly_wage_raw = request.form.get("hourly_wage")

    if not hourly_wage_raw:
        flash("시급 금액을 입력해 주세요.", "error")
        return redirect(url_for("mypage.mypage_page"))

    try:
        hourly_wage = int(hourly_wage_raw)
        if not (0 <= hourly_wage <= MAX_HOURLY_WAGE):
            raise ValueError()
    except ValueError:
        flash(f"올바른 금액(0~{MAX_HOURLY_WAGE:,}원)을 입력해 주세요.", "error")
        return redirect(url_for("mypage.mypage_page"))

    with db() as cursor:
        cursor.execute(
            "UPDATE users SET hourly_wage = %s WHERE id = %s",
            (hourly_wage, user_id)
        )
    
    flash("시급 설정이 정상적으로 수정되었습니다.", "success")
    return redirect(url_for("mypage.mypage_page"))
