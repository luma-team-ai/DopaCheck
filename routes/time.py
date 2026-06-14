"""시간 소비 분석 (FR-9~15)."""
import logging, uuid
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
import ai.comment as ai_comment
from config import BOOK_HOURS, DEFAULT_HOURLY_WAGE, LECTURE_HOURS, WORKOUT_HOURS
from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf

logger = logging.getLogger(__name__)
time_bp = Blueprint('time', __name__, url_prefix='/time')
_MAX_HOURS = 168
_MAX_WAGE = 10_000_000

def calc_sns_conversion(total_sns_hours):
    h = max(0.0, total_sns_hours)
    books = round(h / BOOK_HOURS, 1) if BOOK_HOURS > 0 else 0.0
    lectures = round(h / LECTURE_HOURS, 1) if LECTURE_HOURS > 0 else 0.0
    workouts = round(h / WORKOUT_HOURS, 1) if WORKOUT_HOURS > 0 else 0.0
    return {'books': books, 'lectures': lectures, 'workouts': workouts,
            'books_label': f'책 {books}권', 'lectures_label': f'강의 {lectures}개',
            'workouts_label': f'운동 {workouts}회'}

def calc_game_conversion(game_hours, hourly_wage):
    h, w = max(0.0, game_hours), max(0, hourly_wage)
    cost = round(h * w)
    return {'opportunity_cost': cost, 'label': f'시급 기준 {cost:,}원짜리 취미'}

@time_bp.route('')
@login_required
def time_page():
    return render_template('time/index.html', csrf_token=get_or_create_csrf_token(), default_wage=DEFAULT_HOURLY_WAGE)

@time_bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    verify_csrf()
    user_id = session.get('user_id')
    if not user_id: abort(401)
    try:
        yt = min(_MAX_HOURS, max(0.0, float(request.form.get('youtube_hours') or 0)))
        ig = min(_MAX_HOURS, max(0.0, float(request.form.get('instagram_hours') or 0)))
        tt = min(_MAX_HOURS, max(0.0, float(request.form.get('tiktok_hours') or 0)))
        gm = min(_MAX_HOURS, max(0.0, float(request.form.get('game_hours') or 0)))
        wage = min(_MAX_WAGE, max(0, int(request.form.get('hourly_wage') or DEFAULT_HOURLY_WAGE)))
    except (ValueError, TypeError):
        flash('입력값을 확인해주세요.', 'error')
        return redirect(url_for('time.time_page'))
    total_sns = round(yt + ig + tt, 2)
    sns_conv = calc_sns_conversion(total_sns)
    game_conv = calc_game_conversion(gm, wage)
    chart_data = {'youtube': yt, 'instagram': ig, 'tiktok': tt, 'game': gm}
    rid = str(uuid.uuid4())
    try:
        with db() as cursor:
            cursor.execute('INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (rid, user_id, int(yt*60), int(ig*60), int(tt*60), int(gm*60), wage))
    except Exception as e:
        logger.error('time_records 저장 실패: %s', e)
        flash('결과 저장에 실패했습니다.', 'error')
        return redirect(url_for('time.time_page'))
    comment = ''
    try:
        ctx = {'total_sns_hours': total_sns, 'game_hours': gm,
               'sns_conversion': [sns_conv['books_label'], sns_conv['workouts_label']],
               'game_conversion': game_conv['label']}
        comment = ai_comment.generate('time', ctx)
    except Exception as e:
        logger.warning('코멘트 생성 실패: %s', e)
    try:
        if comment:
            with db() as cursor:
                cursor.execute('UPDATE time_records SET ai_comment=%s WHERE id=%s AND user_id=%s', (comment, rid, user_id))
    except Exception as e:
        logger.warning('코멘트 저장 실패 (비치명적): %s', e)
    _trigger_score_recalc(user_id)
    return render_template('time/result.html', youtube_hours=yt, instagram_hours=ig,
        tiktok_hours=tt, game_hours=gm, total_sns_hours=total_sns, hourly_wage=wage,
        sns_conv=sns_conv, game_conv=game_conv, chart_data=chart_data, comment=comment)

def _trigger_score_recalc(user_id):
    try:
        from routes.score import recalculate_score
        recalculate_score(user_id)
    except NotImplementedError: pass
    except Exception as e:
        logger.warning('점수 재산출 실패 (비치명적): %s', e)
