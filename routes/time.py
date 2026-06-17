"""시간 소비 분석 (담당: 이은석 — FR-9~15)."""
import logging

from flask import Blueprint, render_template, request, session

from ai import comment as ai_comment
from config import BOOK_HOURS, DEFAULT_HOURLY_WAGE, LECTURE_HOURS, WORKOUT_HOURS
from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf
from utils.week import kst_bounds, kst_today, week_bounds

logger = logging.getLogger(__name__)

time_bp = Blueprint("time", __name__, url_prefix="/time")


def _get_week_totals(cursor, user_id: int) -> dict:
    """이번 주(월~일, KST) time_records 앱별 누적 시간(시간 단위)을 반환한다."""
    week_start, week_end = week_bounds(kst_today())
    gte_at, lt_at = kst_bounds(week_start, week_end)
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(youtube_min), 0)   AS yt,
            COALESCE(SUM(instagram_min), 0) AS ig,
            COALESCE(SUM(tiktok_min), 0)    AS tt,
            COALESCE(SUM(game_min), 0)      AS gm
        FROM time_records
        WHERE user_id = %s AND created_at >= %s AND created_at < %s
        """,
        (user_id, gte_at, lt_at),
    )
    row = cursor.fetchone()
    yt = round((row["yt"] or 0) / 60, 1)
    ig = round((row["ig"] or 0) / 60, 1)
    tt = round((row["tt"] or 0) / 60, 1)
    gm = round((row["gm"] or 0) / 60, 1)
    return {
        "week_youtube_h": yt,
        "week_instagram_h": ig,
        "week_tiktok_h": tt,
        "week_game_h": gm,
        "week_total_h": round(yt + ig + tt + gm, 1),
    }


@time_bp.route("")
@login_required
def time_page():
    """앱별 일간 사용 시간 + 이번 주 누적 + 시급 입력 폼. (FR-9, FR-10)"""
    user_id = session["user_id"]
    with db() as cursor:
        cursor.execute("SELECT hourly_wage FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        week = _get_week_totals(cursor, user_id)
    hourly_wage = row["hourly_wage"] if row else DEFAULT_HOURLY_WAGE
    csrf_token = get_or_create_csrf_token()
    return render_template(
        "time/index.html",
        hourly_wage=hourly_wage,
        csrf_token=csrf_token,
        **week,
    )


@time_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """시간 분석 파이프라인.

    1. 유튜브·인스타·틱톡·게임 시간(h) + 시급(원) 입력 검증 (FR-9, FR-10)
    2. SNS 시간 환산: 책 N권 / 강의 N개 / 운동 N회 (FR-11 — config.py 상수)
    3. 게임 시간 환산: 시급 기준 N원짜리 취미 (FR-12)
    4. ai.comment.generate("time", context) 호출 (FR-14)
    5. time_records 저장 + users.hourly_wage 갱신 (FR-15)
    6. 도파민 점수 재산출 트리거 (FR-31) — stub이면 무시
    7. 결과 템플릿 렌더
    """
    verify_csrf()
    user_id = session["user_id"]

    # ── 1. 입력 파싱 & 검증 (FR-9, FR-10) ────────────────────────────
    def _parse_hours(field: str) -> float:
        try:
            val = float(request.form.get(field, 0) or 0)
        except (ValueError, TypeError):
            val = 0.0
        return max(0.0, min(val, 24.0))  # 하루 최대 24h

    youtube_h   = _parse_hours("youtube_h")
    instagram_h = _parse_hours("instagram_h")
    tiktok_h    = _parse_hours("tiktok_h")
    game_h      = _parse_hours("game_h")

    try:
        hourly_wage = int(float(request.form.get("hourly_wage", DEFAULT_HOURLY_WAGE) or DEFAULT_HOURLY_WAGE))
        hourly_wage = max(0, hourly_wage)
    except (ValueError, TypeError):
        hourly_wage = DEFAULT_HOURLY_WAGE

    # ── 2. SNS 시간 환산 (FR-11) ──────────────────────────────────────
    sns_total_h = youtube_h + instagram_h + tiktok_h

    book_n    = round(sns_total_h / BOOK_HOURS, 1)      # 책 N권
    lecture_n = round(sns_total_h / LECTURE_HOURS, 1)   # 강의 N개
    workout_n = round(sns_total_h / WORKOUT_HOURS, 1)   # 운동 N회

    # ── 3. 게임 시간 환산 (FR-12) ─────────────────────────────────────
    game_cost = int(game_h * hourly_wage)               # N원짜리 취미

    # ── P2 합산 168h 초과 검증 ────────────────────────────────────────
    # 각 필드는 0~168h로 클램핑되나 합산은 최대 672h까지 가능.
    # 1주=168h 초과 시 결과는 표시하되 경고 플래그를 템플릿에 전달.
    total_h = sns_total_h + game_h
    over_limit = total_h > 168.0

    # ── 4. AI 공감 코멘트 (FR-14) ─────────────────────────────────────
    context = {
        "youtube_h":   youtube_h,
        "instagram_h": instagram_h,
        "tiktok_h":    tiktok_h,
        "game_h":      game_h,
        "sns_total_h": sns_total_h,
        "book_n":      book_n,
        "lecture_n":   lecture_n,
        "workout_n":   workout_n,
        "game_cost":   game_cost,
        "hourly_wage": hourly_wage,
    }
    try:
        ai_msg = ai_comment.generate("time", context)
    except Exception as exc:
        logger.warning("AI 코멘트 생성 실패 (fallback): %s", exc)
        ai_msg = "이번 주 기록을 잘 남겨주셨어요! 다음 주에는 더 균형 잡힌 시간을 만들어봐요 💪"

    # ── 5. DB 저장 (FR-15) ────────────────────────────────────────────
    youtube_min   = int(youtube_h * 60)
    instagram_min = int(instagram_h * 60)
    tiktok_min    = int(tiktok_h * 60)
    game_min      = int(game_h * 60)

    with db() as cursor:
        cursor.execute(
            """
            INSERT INTO time_records
                (user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_msg),
        )
        # P3-2: 마지막 입력 시급을 users에도 저장 — 다음 방문 시 기억 (UX)
        cursor.execute(
            "UPDATE users SET hourly_wage = %s WHERE id = %s",
            (hourly_wage, user_id),
        )
        # 결과 페이지에 이번 주 누적(오늘 포함) 전달
        week = _get_week_totals(cursor, user_id)

    # ── 6. 도파민 점수 재산출 (FR-31) — stub이면 조용히 무시 ──────────
    # P3-1: score.py 구현 완료 후 최상단 import로 올릴 것 (김승현 PR 완료 시).
    # 현재는 순환 참조 위험을 피하기 위해 함수 내 지연 import 유지.
    try:
        from services.score_service import recalculate_score
        recalculate_score(user_id)
    except NotImplementedError:
        pass  # score.py 미구현 — 점수 갱신 생략
    except Exception as exc:
        logger.warning("점수 재산출 실패 (무시): %s", exc)

    # ── 7. 결과 렌더 ──────────────────────────────────────────────────
    return render_template(
        "time/result.html",
        # 입력값
        youtube_h=youtube_h,
        instagram_h=instagram_h,
        tiktok_h=tiktok_h,
        game_h=game_h,
        hourly_wage=hourly_wage,
        # 계산값
        sns_total_h=sns_total_h,
        total_h=total_h,
        over_limit=over_limit,
        book_n=book_n,
        lecture_n=lecture_n,
        workout_n=workout_n,
        game_cost=game_cost,
        # AI
        ai_comment=ai_msg,
        # 이번 주 누적 (오늘 포함)
        **week,
    )
