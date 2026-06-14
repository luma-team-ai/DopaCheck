"""도파민 점수 + 랭킹 (FR-26~31)."""
import logging, uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, abort, render_template, session
import ai.score as ai_score
from db.client import db
from routes.auth import login_required

logger = logging.getLogger(__name__)
score_bp = Blueprint('score', __name__, url_prefix='/score')
_KST = timezone(timedelta(hours=9))

def _current_week_start():
    now = datetime.now(_KST)
    mon = now - timedelta(days=now.weekday())
    return mon.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

@score_bp.route('')
@login_required
def score_page():
    user_id = session.get('user_id')
    if not user_id: abort(401)
    ws = _current_week_start()
    with db() as c:
        c.execute('SELECT score, delivery_contribution, time_contribution, challenge_bonus FROM dopamine_scores WHERE user_id=%s AND week_start=%s', (user_id, ws))
        my_score = c.fetchone()
        c.execute('SELECT AVG(score) AS avg_score FROM dopamine_scores WHERE week_start=%s', (ws,))
        row = c.fetchone()
        avg_score = round(float(row['avg_score'] or 0), 1) if row else 0.0
        rank_pct = None
        if my_score:
            c.execute('SELECT COUNT(*) AS cnt FROM dopamine_scores WHERE week_start=%s AND score>%s', (ws, my_score['score']))
            higher = c.fetchone()['cnt']
            c.execute('SELECT COUNT(*) AS cnt FROM dopamine_scores WHERE week_start=%s', (ws,))
            total = c.fetchone()['cnt']
            rank_pct = round((higher + 1) / total * 100) if total > 0 else None
    return render_template('score/index.html', my_score=my_score, avg_score=avg_score, rank_pct=rank_pct, week_start=ws)

def recalculate_score(user_id):
    ws = _current_week_start()
    with db() as c:
        c.execute('SELECT COALESCE(SUM(total_price),0) AS total FROM delivery_records WHERE user_id=%s AND created_at>=%s', (user_id, ws))
        d_total = int(c.fetchone()['total'])
        c.execute('SELECT COALESCE(SUM(youtube_min+instagram_min+tiktok_min+game_min),0) AS total FROM time_records WHERE user_id=%s AND created_at>=%s', (user_id, ws))
        t_total = int(c.fetchone()['total'])
        c.execute('SELECT COUNT(*) AS cnt FROM user_challenges WHERE user_id=%s AND is_completed=1 AND completed_at>=%s', (user_id, ws))
        ch = int(c.fetchone()['cnt'])
        result = ai_score.calculate({'delivery_total': d_total, 'time_total_min': t_total, 'challenge_completed': ch})
        sid = str(uuid.uuid4())
        c.execute('INSERT INTO dopamine_scores (id,user_id,week_start,score,delivery_contribution,time_contribution,challenge_bonus) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE score=VALUES(score),delivery_contribution=VALUES(delivery_contribution),time_contribution=VALUES(time_contribution),challenge_bonus=VALUES(challenge_bonus)',
            (sid, user_id, ws, result['score'], result['delivery_contribution'], result['time_contribution'], result['challenge_bonus']))
    logger.info('점수 재산출 완료: user_id=%s, score=%s', user_id, result['score'])
