"""분석 히스토리 (담당: 허남 — FR-21~25)."""
import logging
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, abort, jsonify, render_template, request, session

logger = logging.getLogger(__name__)

_VALID_TYPES = frozenset({"delivery", "time"})

from db.client import get_supabase
from routes.auth import login_required

history_bp = Blueprint("history", __name__, url_prefix="/history")

_KST = timezone(timedelta(hours=9))


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def _month_start() -> str:
    return date.today().replace(day=1).isoformat()


def _date_label(d: date) -> str:
    today = date.today()
    if d == today:
        return f"오늘, {d.month}월 {d.day}일"
    if d == today - timedelta(days=1):
        return f"어제, {d.month}월 {d.day}일"
    return f"{d.month}월 {d.day}일"


def _enrich(records: list[dict], record_type: str) -> list[dict]:
    """created_at → date / time_label / date_label / summary 필드 추가."""
    for r in records:
        r["type"] = record_type
        try:
            dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(_KST)
        except Exception as e:
            logger.warning("created_at 파싱 실패: %s", e)
            dt = datetime.now(_KST)
        r["date"] = dt.strftime("%Y-%m-%d")
        r["date_label"] = _date_label(dt.date())
        hour, minute = dt.hour, dt.minute
        ampm = "오전" if hour < 12 else "오후"
        h12 = hour % 12 or 12
        r["time_label"] = f"{ampm} {h12}:{minute:02d}"
        if record_type == "delivery":
            price = r.get("total_price") or 0
            kcal = r.get("total_calories") or 0
            r["summary"] = f"배달 {price:,}원 · {kcal:,} kcal"
        else:
            mins = [
                ("유튜브", r.get("youtube_min") or 0),
                ("인스타", r.get("instagram_min") or 0),
                ("틱톡", r.get("tiktok_min") or 0),
                ("게임", r.get("game_min") or 0),
            ]
            top = max(mins, key=lambda x: x[1])
            others = sum(1 for _, m in mins if m > 0) - 1
            label = f"{top[0]} {top[1]}분"
            if others > 0:
                label += f" 외 {others}개 앱"
            r["summary"] = label
    return records


@history_bp.route("")
@login_required
def history_list():
    """날짜별 분석 기록 목록. (FR-21, FR-24, FR-25)"""
    user_id = session["user"]["id"]
    period = request.args.get("period", "all")
    type_filter = request.args.get("type_filter", "all")

    supabase = get_supabase()

    delivery_q = supabase.table("delivery_records").select(
        "id, total_price, total_calories, ai_comment, created_at"
    ).eq("user_id", user_id)

    time_q = supabase.table("time_records").select(
        "id, youtube_min, instagram_min, tiktok_min, game_min, ai_comment, created_at"
    ).eq("user_id", user_id)

    if period == "week":
        cutoff = _week_start()
        delivery_q = delivery_q.gte("created_at", cutoff)
        time_q = time_q.gte("created_at", cutoff)
    elif period == "month":
        cutoff = _month_start()
        delivery_q = delivery_q.gte("created_at", cutoff)
        time_q = time_q.gte("created_at", cutoff)

    try:
        delivery_records = _enrich(
            delivery_q.order("created_at", desc=True).execute().data or [], "delivery"
        )
        time_records = _enrich(
            time_q.order("created_at", desc=True).execute().data or [], "time"
        )
    except Exception as e:
        logger.warning("히스토리 목록 조회 실패: %s", e)
        abort(503)

    if type_filter == "delivery":
        all_records = delivery_records
    elif type_filter == "time":
        all_records = time_records
    else:
        all_records = sorted(
            delivery_records + time_records,
            key=lambda r: r["created_at"],
            reverse=True,
        )

    groups: dict[str, dict] = {}
    for r in all_records:
        key = r["date"]
        if key not in groups:
            groups[key] = {"label": r["date_label"], "records": []}
        groups[key]["records"].append(r)

    return render_template(
        "history/index.html",
        grouped=list(groups.values()),
        period=period,
        type_filter=type_filter,
    )


@history_bp.route("/<record_id>")
@login_required
def history_detail(record_id: str):
    """특정 기록 상세 조회. (FR-22)"""
    user_id = session["user"]["id"]
    record_type = request.args.get("type", "delivery")

    if record_type not in _VALID_TYPES:
        return jsonify({"error": "잘못된 타입"}), 400

    supabase = get_supabase()
    table = "delivery_records" if record_type == "delivery" else "time_records"

    try:
        result = (
            supabase.table(table)
            .select("*")
            .eq("id", record_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        logger.warning("히스토리 상세 조회 실패: %s", e)
        abort(503)

    row = result.data[0] if result.data else None

    if not row:
        return render_template("history/detail.html", record=None, record_type=record_type), 404

    _enrich([row], record_type)
    return render_template("history/detail.html", record=row, record_type=record_type)


@history_bp.route("/<record_id>", methods=["DELETE"])
@login_required
def history_delete(record_id: str):
    """기록 삭제. (FR-23)"""
    user_id = session["user"]["id"]
    record_type = request.args.get("type", "delivery")

    if record_type not in _VALID_TYPES:
        return jsonify({"error": "잘못된 타입"}), 400

    table = "delivery_records" if record_type == "delivery" else "time_records"

    supabase = get_supabase()
    try:
        existing = (
            supabase.table(table)
            .select("id")
            .eq("id", record_id)
            .eq("user_id", user_id)
            .execute()
            .data
        )
    except Exception as e:
        logger.warning("히스토리 삭제 전 조회 실패: %s", e)
        abort(503)

    if not existing:
        return jsonify({"error": "기록을 찾을 수 없거나 삭제 권한이 없습니다."}), 404

    try:
        supabase.table(table).delete().eq("id", record_id).execute()
    except Exception as e:
        logger.warning("히스토리 삭제 실패: %s", e)
        abort(503)

    return "", 204
