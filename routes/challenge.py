"""AI 챌린지 (담당: 오영석 — FR-32~38)."""
import logging
import uuid

from flask import Blueprint, jsonify, redirect, render_template, session, url_for

import ai.challenge as ai_challenge
from db.client import get_supabase
from routes.auth import login_required

logger = logging.getLogger(__name__)

challenge_bp = Blueprint("challenge", __name__, url_prefix="/challenge")


@challenge_bp.route("")
@login_required
def challenge_page():
    """챌린지 목록 페이지.

    1. 기본 챌린지 목록 조회 (FR-32)
    2. 히스토리 1건 이상이면 ai.challenge.recommend(history) 호출 (FR-33)
    3. 참여 중 챌린지 달성률 프로그레스 바 (FR-36)
    """
    user_id = session.get("user", {}).get("id")
    if not user_id:
        return redirect(url_for("auth.login_page"))
    supabase = get_supabase()

    # 기본 챌린지 목록 (FR-32)
    try:
        challenges = supabase.table("challenges").select("*").execute().data or []
    except Exception as e:
        logger.warning("챌린지 목록 조회 실패: %s", e)
        challenges = []

    # 사용자 참여 중 챌린지 (FR-36)
    try:
        user_challenges = (
            supabase.table("user_challenges")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_completed", False)
            .execute()
            .data or []
        )
    except Exception as e:
        logger.warning("사용자 챌린지 조회 실패: %s", e)
        user_challenges = []

    joined_ids = {uc["challenge_id"] for uc in user_challenges}
    progress_map = {uc["challenge_id"]: uc["progress"] for uc in user_challenges}

    # AI 추천 (FR-33) — 히스토리 1건 이상일 때
    ai_recommendations = []
    try:
        deliveries = (
            supabase.table("delivery_records")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data or []
        )
        times = (
            supabase.table("time_records")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data or []
        )
        if deliveries or times:
            delivery_rows = (
                supabase.table("delivery_records")
                .select("created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data or []
            )
            time_rows = (
                supabase.table("time_records")
                .select("youtube_min, instagram_min, tiktok_min, game_min")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data or []
            )

            weeks = max(1, len(delivery_rows) // 7)  # 정수 주 단위
            avg_delivery = len(delivery_rows) / weeks

            app_totals = {"youtube": 0, "instagram": 0, "tiktok": 0, "game": 0}
            for t in time_rows:
                app_totals["youtube"] += t.get("youtube_min", 0)
                app_totals["instagram"] += t.get("instagram_min", 0)
                app_totals["tiktok"] += t.get("tiktok_min", 0)
                app_totals["game"] += t.get("game_min", 0)

            top_app = max(app_totals, key=app_totals.get)
            top_app_hours = app_totals[top_app] / 60

            result = ai_challenge.recommend({
                "avg_delivery_per_week": avg_delivery,
                "top_app": top_app,
                "top_app_hours": top_app_hours,
            })
            ai_recommendations = result.get("recommendations", [])
    except Exception as e:
        logger.warning("AI 챌린지 추천 실패: %s", e)

    return render_template(
        "challenge/index.html",
        challenges=challenges,
        joined_ids=joined_ids,
        progress_map=progress_map,
        ai_recommendations=ai_recommendations,
    )


@challenge_bp.route("/<challenge_id>/join", methods=["POST"])
@login_required
def join(challenge_id: str):
    """챌린지 참여 + 목표 설정. (FR-34)

    동일 챌린지 활성 상태 중복 참여 차단 (FR-35 — DB unique index와 이중 방어)
    """
    user_id = session.get("user", {}).get("id")
    if not user_id:
        return redirect(url_for("auth.login_page"))

    try:
        uuid.UUID(challenge_id)
    except ValueError:
        return jsonify({"error": "잘못된 챌린지 ID입니다."}), 400

    supabase = get_supabase()

    # 중복 참여 사전 체크 (FR-35)
    try:
        existing = (
            supabase.table("user_challenges")
            .select("id")
            .eq("user_id", user_id)
            .eq("challenge_id", challenge_id)
            .eq("is_completed", False)
            .execute()
            .data
        )
    except Exception as e:
        logger.warning("챌린지 중복 체크 실패: %s", e)
        return jsonify({"error": "서버 오류가 발생했습니다."}), 503

    if existing:
        return jsonify({"error": "이미 참여 중인 챌린지입니다."}), 409

    try:
        supabase.table("user_challenges").insert({
            "user_id": user_id,
            "challenge_id": challenge_id,
            "progress": 0,
            "is_completed": False,
        }).execute()
    except Exception as e:
        err_str = str(e)
        if "23505" in err_str or "unique" in err_str.lower():
            return jsonify({"error": "이미 참여 중인 챌린지입니다."}), 409
        logger.warning("챌린지 참여 실패: %s", e)
        return jsonify({"error": "서버 오류가 발생했습니다."}), 503

    return jsonify({"success": True, "message": "챌린지에 참여했습니다!"}), 201
