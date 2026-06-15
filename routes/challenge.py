"""AI 챌린지 (담당: 오영석 — FR-32~38)."""
import logging
import time

from flask import Blueprint, jsonify, render_template, session

import ai.challenge as ai_challenge
from config import AI_RECOMMEND_CACHE_TTL
from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf

logger = logging.getLogger(__name__)

challenge_bp = Blueprint("challenge", __name__, url_prefix="/challenge")

# ── AI 추천 세션 캐시 키 ──────────────────────────────────
_AI_CACHE_KEY = "ai_recommendations"
_AI_CACHE_TS_KEY = "ai_recommendations_ts"


def _calc_avg_delivery_per_week(delivery_rows: list) -> float:
    """delivery_rows의 created_at 최솟값·최댓값 실제 날짜 범위로 주 수를 산정한다.

    - 0건 또는 1건: 주 수를 1로 처리해 0 division 방지.
    - 날짜 범위가 7일 미만이어도 최소 1주로 보정한다.
    """
    if len(delivery_rows) <= 1:
        return float(len(delivery_rows))

    from datetime import datetime

    dates = []
    for row in delivery_rows:
        raw = row.get("created_at")
        if raw is None:
            continue
        if isinstance(raw, str):
            # KST-naive 문자열 → datetime 변환
            try:
                dates.append(datetime.fromisoformat(raw))
            except ValueError:
                pass
        else:
            # datetime 객체 그대로 사용
            dates.append(raw)

    if not dates:
        # created_at 컬럼이 없거나 파싱 실패 → fallback: 건수 기반
        weeks = max(1, len(delivery_rows) // 7)
        return len(delivery_rows) / weeks

    min_date = min(dates)
    max_date = max(dates)
    days_range = max(1, (max_date - min_date).days + 1)  # +1: 당일 포함
    weeks = max(1, days_range / 7)
    return len(delivery_rows) / weeks


@challenge_bp.route("")
@login_required
def challenge_page():
    """챌린지 목록 페이지.

    1. 기본 챌린지 목록 조회 (FR-32)
    2. 히스토리 1건 이상이면 ai.challenge.recommend(history) 호출 (FR-33)
       — 세션 캐시(TTL: AI_RECOMMEND_CACHE_TTL) 로 페이지 로드마다 LLM 호출 방지
    3. 참여 중 챌린지 달성률 프로그레스 바 (FR-36)
    """
    user_id = session.get("user_id")

    # CSRF 토큰 생성 (join POST에서 검증)
    csrf_token = get_or_create_csrf_token()

    # 기본 챌린지 목록 (FR-32)
    try:
        with db() as cursor:
            cursor.execute(
                "SELECT id, title, description, target_type, target_value"
                " FROM challenges"
            )
            challenges = cursor.fetchall() or []
    except Exception as e:
        logger.warning("챌린지 목록 조회 실패: %s", e)
        challenges = []

    # 사용자 참여 중 챌린지 (FR-36)
    try:
        with db() as cursor:
            cursor.execute(
                "SELECT challenge_id, progress"
                " FROM user_challenges WHERE user_id = %s AND is_completed = 0",
                (user_id,),
            )
            user_challenges = cursor.fetchall() or []
    except Exception as e:
        logger.warning("사용자 챌린지 조회 실패: %s", e)
        user_challenges = []

    joined_ids = {uc["challenge_id"] for uc in user_challenges}
    progress_map = {uc["challenge_id"]: uc["progress"] for uc in user_challenges}

    # AI 추천 (FR-33) — 세션 캐시로 TTL 내 중복 LLM 호출 방지
    ai_recommendations = _get_ai_recommendations(user_id)

    return render_template(
        "challenge/index.html",
        challenges=challenges,
        joined_ids=joined_ids,
        progress_map=progress_map,
        ai_recommendations=ai_recommendations,
        csrf_token=csrf_token,
    )


def _get_ai_recommendations(user_id: int) -> list:
    """AI 챌린지 추천을 반환한다. 세션 캐시(TTL=AI_RECOMMEND_CACHE_TTL) 내이면 캐시 반환."""
    # 캐시 유효성 확인 (사용자별: user_id 포함 키)
    cached = session.get(_AI_CACHE_KEY)
    cached_ts = session.get(_AI_CACHE_TS_KEY)
    cached_uid = session.get("ai_recommendations_uid")

    now = time.time()
    if (
        cached is not None
        and cached_ts is not None
        and cached_uid == user_id
        and (now - cached_ts) < AI_RECOMMEND_CACHE_TTL
    ):
        logger.debug("AI 추천 캐시 적중 (TTL 남은 시간: %.0f초)", AI_RECOMMEND_CACHE_TTL - (now - cached_ts))
        return cached

    # 캐시 미스 — DB 조회 후 LLM 호출
    try:
        with db() as cursor:
            cursor.execute(
                "SELECT id FROM delivery_records WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            has_delivery = cursor.fetchone()
            cursor.execute(
                "SELECT id FROM time_records WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            has_time = cursor.fetchone()

        if not (has_delivery or has_time):
            return []

        with db() as cursor:
            cursor.execute(
                "SELECT created_at FROM delivery_records"
                " WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
            delivery_rows = cursor.fetchall() or []
            cursor.execute(
                "SELECT youtube_min, instagram_min, tiktok_min, game_min"
                " FROM time_records"
                " WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
            time_rows = cursor.fetchall() or []

        # 실제 날짜 범위 기반 주 수 산정 (0division 방지 포함)
        avg_delivery = _calc_avg_delivery_per_week(delivery_rows)

        app_totals = {"youtube": 0, "instagram": 0, "tiktok": 0, "game": 0}
        for t in time_rows:
            app_totals["youtube"] += t.get("youtube_min", 0) or 0
            app_totals["instagram"] += t.get("instagram_min", 0) or 0
            app_totals["tiktok"] += t.get("tiktok_min", 0) or 0
            app_totals["game"] += t.get("game_min", 0) or 0

        history: dict = {"avg_delivery_per_week": avg_delivery}
        total_app_min = sum(app_totals.values())
        if total_app_min > 0:
            top_app = max(app_totals, key=app_totals.get)
            history["top_app"] = top_app
            history["top_app_hours"] = app_totals[top_app] / 60

        result = ai_challenge.recommend(history)
        recommendations = result.get("recommendations", [])

        # 세션 쿠키 4KB 한도 초과 방지 — 항목별 문자열 truncate 후 저장
        _TITLE_MAX = 50
        _DESC_MAX = 200
        truncated = []
        for rec in recommendations:
            if isinstance(rec, dict):
                truncated.append({
                    k: (v[:_TITLE_MAX] if k == "title" and isinstance(v, str) else
                        v[:_DESC_MAX] if k == "description" and isinstance(v, str) else v)
                    for k, v in rec.items()
                })
            else:
                truncated.append(rec)
        recommendations = truncated

        # 세션에 캐시 저장
        session[_AI_CACHE_KEY] = recommendations
        session[_AI_CACHE_TS_KEY] = now
        session["ai_recommendations_uid"] = user_id

        return recommendations

    except Exception as e:
        logger.warning("AI 챌린지 추천 실패: %s", e)
        return []


@challenge_bp.route("/<challenge_id>/join", methods=["POST"])
@login_required
def join(challenge_id: str):
    """챌린지 참여 + 목표 설정. (FR-34)

    동일 챌린지 활성 상태 중복 참여 차단 (FR-35 — 앱 레벨 검증, MariaDB partial index 미지원)
    CSRF 검증 (세션 토큰 — X-CSRF-Token 헤더 또는 csrf_token 폼 필드)
    """
    # CSRF 검증 (불일치 시 403)
    verify_csrf()

    user_id = session.get("user_id")

    # 정수 검증 (challenges.id = bigint)
    try:
        challenge_id_int = int(challenge_id)
    except (ValueError, TypeError):
        return jsonify({"error": "잘못된 챌린지 ID입니다."}), 400

    # 중복 참여 사전 체크 (FR-35)
    try:
        with db() as cursor:
            cursor.execute(
                "SELECT id FROM user_challenges"
                " WHERE user_id = %s AND challenge_id = %s AND is_completed = 0",
                (user_id, challenge_id),
            )
            existing = cursor.fetchone()
    except Exception as e:
        logger.warning("챌린지 중복 체크 실패: %s", e)
        return jsonify({"error": "서버 오류가 발생했습니다."}), 503

    if existing:
        return jsonify({"error": "이미 참여 중인 챌린지입니다."}), 409

    try:
        with db() as cursor:
            cursor.execute(
                "INSERT INTO user_challenges (user_id, challenge_id, progress, is_completed)"
                " VALUES (%s, %s, 0, 0)",
                (user_id, challenge_id_int),
            )
    except Exception as e:
        logger.warning("챌린지 참여 실패: %s", e)
        return jsonify({"error": "서버 오류가 발생했습니다."}), 503

    return jsonify({"success": True, "message": "챌린지에 참여했습니다!"}), 201
