"""분석 히스토리 (담당: 허남 — FR-21~25)."""
import logging
import uuid
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, jsonify, render_template, request, session

from utils.week import KST, kst_bounds, kst_today, week_bounds

logger = logging.getLogger(__name__)

_VALID_TYPES = frozenset({"delivery", "time"})
_VALID_PERIODS = frozenset({"week", "month", "all"})
# P1: 테이블명을 화이트리스트 딕셔너리로 관리 — 동적 테이블명은 반드시 이 매핑으로만 해석한다 (SQLi 방지).
TABLE_MAP: dict[str, str] = {
    "delivery": "delivery_records",
    "time":     "time_records",
}


def _valid_uuid(value: str) -> bool:
    """record_id가 UUID 형식인지 검증한다 (예측 불가 입력 차단)."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False

from db.client import db
from routes.auth import login_required

history_bp = Blueprint("history", __name__, url_prefix="/history")


def _date_label(d: date) -> str:
    today = kst_today()
    if d == today:
        return f"오늘, {d.month}월 {d.day}일"
    if d == today - timedelta(days=1):
        return f"어제, {d.month}월 {d.day}일"
    return f"{d.month}월 {d.day}일"


def _enrich(records: list[dict], record_type: str) -> list[dict]:
    """created_at → date / time_label / date_label / summary 필드 추가.

    주의: 전달받은 dict를 in-place로 변이(mutation)한다. DB 조회 직후 일회성으로만
    사용하므로 부작용이 없으나, 캐시된 dict 재사용 시에는 복사본을 전달할 것.
    """
    for r in records:
        r["type"] = record_type
        try:
            raw = r["created_at"]
            if isinstance(raw, datetime):
                # MariaDB DATETIME(naive) → KST로 간주. tz 정보가 없으면 KST 부여.
                dt = (raw if raw.tzinfo else raw.replace(tzinfo=KST)).astimezone(KST)
            else:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(KST)
        except Exception as e:
            logger.warning("created_at 파싱 실패: %s", e)
            dt = datetime.now(KST)
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
@login_required  # 비로그인 차단 — if not user_id: abort(401) 대신 데코레이터로 위임 (P1 수정)
def history_list():
    """날짜별 분석 기록 목록. (FR-21, FR-24, FR-25)"""
    user_id = session.get("user_id")
    period = request.args.get("period", "all")
    type_filter = request.args.get("type_filter", "all")

    if period not in _VALID_PERIODS:
        period = "all"  # 임의 값은 조용히 'all'로 정규화

    # type_filter는 'all' 또는 _VALID_TYPES만 허용 (detail/delete와 검증 일관성)
    if type_filter != "all" and type_filter not in _VALID_TYPES:
        return jsonify({"error": "잘못된 타입"}), 400

    # 기간 경계 [시작, 익기간) — report.py(kst_bounds)와 동일한 exclusive 상한 패턴.
    # 상한 없이 >= 만 쓰면 미래 기록까지 포함되므로 created_at < 상한을 함께 바인딩한다.
    bounds: tuple[str, str] | None = None
    if period == "week":
        bounds = kst_bounds(*week_bounds(kst_today()))
    elif period == "month":
        first = kst_today().replace(day=1)
        next_first = (first + timedelta(days=32)).replace(day=1)
        bounds = (f"{first.isoformat()} 00:00:00", f"{next_first.isoformat()} 00:00:00")

    # RLS 대체: 모든 쿼리에 WHERE user_id = %s 앱 필터 + %s 파라미터 바인딩.
    delivery_sql = (
        "SELECT id, total_price, total_calories, ai_comment, created_at "
        "FROM delivery_records WHERE user_id = %s"
    )
    time_sql = (
        "SELECT id, youtube_min, instagram_min, tiktok_min, game_min, ai_comment, created_at "
        "FROM time_records WHERE user_id = %s"
    )
    delivery_params: list = [user_id]
    time_params: list = [user_id]
    if bounds is not None:
        delivery_sql += " AND created_at >= %s AND created_at < %s"
        time_sql += " AND created_at >= %s AND created_at < %s"
        delivery_params.extend(bounds)
        time_params.extend(bounds)
    delivery_sql += " ORDER BY created_at DESC"
    time_sql += " ORDER BY created_at DESC"

    try:
        with db() as cursor:
            cursor.execute(delivery_sql, tuple(delivery_params))
            delivery_rows = cursor.fetchall() or []
            cursor.execute(time_sql, tuple(time_params))
            time_rows = cursor.fetchall() or []
    except Exception as e:
        logger.warning("히스토리 목록 조회 실패: %s", e)
        abort(503)

    delivery_records = _enrich(delivery_rows, "delivery")
    time_records = _enrich(time_rows, "time")

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
@login_required  # 비로그인 차단 — if not user_id: abort(401) 대신 데코레이터로 위임 (P1 수정)
def history_detail(record_id: str):
    """특정 기록 상세 조회. (FR-22)"""
    user_id = session.get("user_id")
    record_type = request.args.get("type", "delivery")

    if not _valid_uuid(record_id):
        abort(400)
    if record_type not in _VALID_TYPES:
        return jsonify({"error": "잘못된 타입"}), 400

    # P1: 테이블명을 TABLE_MAP 화이트리스트에서 가져옴 — 사용자 입력 직접 삽입 불가.
    table = TABLE_MAP[record_type]

    try:
        with db() as cursor:
            cursor.execute(
                "SELECT * FROM " + table + " WHERE id = %s AND user_id = %s",
                (record_id, user_id),
            )
            row = cursor.fetchone()
    except Exception as e:
        logger.warning("히스토리 상세 조회 실패: %s", e)
        abort(503)

    if not row:
        return render_template("history/detail.html", record=None, record_type=record_type), 404

    _enrich([row], record_type)
    return render_template("history/detail.html", record=row, record_type=record_type)


@history_bp.route("/<record_id>", methods=["DELETE"])
@login_required  # 비로그인 차단 — if not user_id: abort(401) 대신 데코레이터로 위임 (P1 수정)
def history_delete(record_id: str):
    """기록 삭제. (FR-23)"""
    user_id = session.get("user_id")
    record_type = request.args.get("type", "delivery")

    if not _valid_uuid(record_id):
        abort(400)
    if record_type not in _VALID_TYPES:
        return jsonify({"error": "잘못된 타입"}), 400

    # P1: 테이블명을 TABLE_MAP 화이트리스트에서 가져옴 — 사용자 입력 직접 삽입 불가.
    table = TABLE_MAP[record_type]

    # 404 분기를 with 블록 밖으로 빼 트랜잭션 경계를 명확히 한다
    # (조기 return이 yield~commit 사이에 끼지 않도록 — 향후 쓰기 추가 시 의도치 않은 commit 방지).
    existing = None
    try:
        with db() as cursor:
            # 사전 조회 — 타인 기록/없는 기록 구분 (404 vs 204)
            cursor.execute(
                "SELECT id FROM " + table + " WHERE id = %s AND user_id = %s",
                (record_id, user_id),
            )
            existing = cursor.fetchone()
            if existing:
                # IDOR 방어: 삭제 쿼리에도 user_id 필터를 명시 (사전 조회와 이중 방어)
                cursor.execute(
                    "DELETE FROM " + table + " WHERE id = %s AND user_id = %s",
                    (record_id, user_id),
                )
    except Exception as e:
        logger.warning("히스토리 삭제 실패: %s", e)
        abort(503)

    if not existing:
        return jsonify({"error": "기록을 찾을 수 없거나 삭제 권한이 없습니다."}), 404
    return "", 204
