"""도파민 점수 + 랭킹 (담당: 김승현 — FR-26~31)."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, render_template, session

import ai.score as ai_score
from db.client import db
from routes.auth import login_required

logger = logging.getLogger(__name__)
score_bp = Blueprint("score", __name__, url_prefix="/score")
_KST = timezone(timedelta(hours=9))

def _current_week_start() -> str:
    now = datetime.now(_KST)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

@score_bp.route("")
@login_required
def score_page():
    user_id = session.get("user_id")
    if not user_id:
        abort(401)
    week_start = _current_week_start()
    with db() as cursor:
        cursor.execute("SELECT score, delivery_contribution, time_contribution, challenge_bonus FROM dopamine_scores WHERE user_id = %s AND week_start = %s", (user_id, week_start))
        my_score = cursor.fetchone()
        cursor.execute("SELECT AVG(score) AS avg_score FROM dopamine_scores WHERE week_start = %s", (week_start,))
        avg_row = cursor.fetchone()
        avg_score = round(float(avg_row["avg_score"] or 0), 1) if avg_row else 0.0
        rank_pct = None
        if my_score:
            cursor.execute("SELECT COUNT(*) AS cnt FROM dopamine_scores WHERE week_start = %s AND score >= %s", (week_start, my_score["score"]))
            higher_or_equal = cursor.fetchone()["cnt"]
            cursor.execute("SELECT COUNT(*) AS cnt FROM dopamine_scores WHERE week_start = %s", (week_start,))
            total = cursor.fetchone()["cnt"]
            rank_pct = round(higher_or_equal / total * 100) if total > 0 else None
    return render_template("score/index.html", my_score=my_score, avg_score=avg_score, rank_pct=rank_pct, week_start=week_start)

def recalculate_score(user_id) -> None:
    week_start = _current_week_start()
    with db() as cursor:
        cursor.execute("SELECT COALESCE(SUM(total_price), 0) AS total FROM delivery_records WHERE user_id = %s AND created_at >= %s", (user_id, week_start))
        delivery_total = int(cursor.fetchone()["total"])
        cursor.execute("SELECT COALESCE(SUM(youtube_min + instagram_min + tiktok_min + game_min), 0) AS total FROM time_records WHERE user_id = %s AND created_at >= %s", (user_id, week_start))
        time_total_min = int(cursor.fetchone()["total"])
        cursor.execute("SELECT COUNT(*) AS cnt FROM user_challenges WHERE user_id = %s AND is_completed = 1 AND completed_at >= %s", (user_id, week_start))
        challenge_completed = int(cursor.fetchone()["cnt"])
    result = ai_score.calculate({"delivery_total": delivery_total, "time_total_min": time_total_min, "challenge_completed": challenge_completed})
    score_id = str(uuid.uuid4())
    with db() as cursor:
        cursor.execute("INSERT INTO dopamine_scores (id, user_id, week_start, score, delivery_contribution, time_contribution, challenge_bonus) VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE score = VALUES(score), delivery_contribution = VALUES(delivery_contribution), time_contribution = VALUES(time_contribution), challenge_bonus = VALUES(challenge_bonus)", (score_id, user_id, week_start, result["score"], result["delivery_contribution"], result["time_contribution"], result["challenge_bonus"]))
    logger.info("점수 재산출 완료: user_id=%s, score=%s", user_id, result["score"])
