"""시간 소비 분석 (담당: 이은석 — FR-9~15)."""
import json
import logging
import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

import ai.comment as ai_comment
from config import BOOK_HOURS, DEFAULT_HOURLY_WAGE, LECTURE_HOURS, WORKOUT_HOURS
from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf

logger = logging.getLogger(__name__)
time_bp = Blueprint("time", __name__, url_prefix="/time")
_MAX_HOURS_PER_APP = 168
_MAX_HOURLY_WAGE = 10_000_000

def calc_sns_conversion(total_sns_hours: float) -> dict:
    hours = max(0.0, total_sns_hours)
    books = round(hours / BOOK_HOURS, 1) if BOOK_HOURS > 0 else 0.0
    lectures = round(hours / LECTURE_HOURS, 1) if LECTURE_HOURS > 0 else 0.0
    workouts = round(hours / WORKOUT_HOURS, 1) if WORKOUT_HOURS > 0 else 0.0
    return {"books": books, "lectures": lectures, "workouts": workouts, "books_label": f"책 {books}권", "lectures_label": f"강의 {lectures}개", "workouts_label": f"운동 {workouts}회"}

def calc_game_conversion(game_hours: float, hourly_wage: int) -> dict:
    hours = max(0.0, game_hours)
    wage = max(0, hourly_wage)
    cost = round(hours * wage)
    return {"opportunity_cost": cost, "label": f"시급 기준 {cost:,}원짜리 취미"}

@time_bp.route("")
@login_required
def time_page():
    csrf_token = get_or_create_csrf_token()
    return render_template("time/index.html", csrf_token=csrf_token, default_wage=DEFAULT_HOURLY_WAGE)

@time_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    verify_csrf()
    user_id = session.get("user_id")
    if not user_id:
        abort(401)
    try:
        youtube_hours = min(_MAX_HOURS_PER_APP, max(0.0, float(request.form.get("youtube_hours") or 0)))
        instagram_hours = min(_MAX_HOURS_PER_APP, max(0.0, float(request.form.get("instagram_hours") or 0)))
        tiktok_hours = min(_MAX_HOURS_PER_APP, max(0.0, float(request.form.get("tiktok_hours") or 0)))
        game_hours = min(_MAX_HOURS_PER_APP, max(0.0, float(request.form.get("game_hours") or 0)))
        hourly_wage = min(_MAX_HOURLY_WAGE, max(0, int(request.form.get("hourly_wage") or DEFAULT_HOURLY_WAGE)))
    except (ValueError, TypeError):
        flash("입력값을 확인해주세요.", "error")
        return redirect(url_for("time.time_page"))
    total_sns_hours = round(youtube_hours + instagram_hours + tiktok_hours, 2)
    sns_conv = calc_sns_conversion(total_sns_hours)
    game_conv = calc_game_conversion(game_hours, hourly_wage)
    chart_data = {"youtube": youtube_hours, "instagram": instagram_hours, "tiktok": tiktok_hours, "game": game_hours}
    conversions = [sns_conv["books_label"], sns_conv["workouts_label"]]
    comment = ""
    try:
        context = {"total_sns_hours": total_sns_hours, "game_hours": game_hours, "sns_conversion": conversions, "game_conversion": game_conv["label"]}
        comment = ai_comment.generate("time", context)
    except Exception as e:
        logger.warning("코멘트 생성 실패: %s", e)
    record_id = str(uuid.uuid4())
    try:
        with db() as cursor:
            cursor.execute("INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (record_id, user_id, int(youtube_hours * 60), int(instagram_hours * 60), int(tiktok_hours * 60), int(game_hours * 60), hourly_wage, comment))
    except Exception as e:
        logger.error("time_records 저장 실패: %s", e)
        flash("결과 저장에 실패했습니다.", "error")
        return redirect(url_for("time.time_page"))
    try:
        from routes.score import recalculate_score
        recalculate_score(user_id)
    except NotImplementedError:
        pass
    except Exception as e:
        logger.warning("점수 재산출 실패 (비치명적): %s", e)
    return render_template("time/result.html", youtube_hours=youtube_hours, instagram_hours=instagram_hours, tiktok_hours=tiktok_hours, game_hours=game_hours, total_sns_hours=total_sns_hours, hourly_wage=hourly_wage, sns_conv=sns_conv, game_conv=game_conv, chart_data=chart_data, comment=comment)
