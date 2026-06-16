# routes/admin.py
import json
import logging
import uuid as _uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from db.client import db
from routes.auth import login_required
from utils.csrf import get_or_create_csrf_token, verify_csrf
from utils.week import KST, kst_today

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _mask_email(email: str) -> str:
    """이메일 로컬파트 일부를 마스킹한다. (PII 노출 축소 — P2)

    예: "abcdef@example.com" -> "ab****@example.com"
    """
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


def admin_required(view):
    """관리자 권한을 강제하는 데코레이터.
    
    비관리자(role != 'admin') 접근 시 에러 노출 없이 홈('/')으로 리다이렉트합니다. (FR-54)
    """
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")

        # 세션 캐시 대신 매 요청마다 DB에서 최신 역할을 조회한다.
        # (관리자 권한 회수가 즉시 반영되도록 보장 — P2)
        with db() as cursor:
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            role = user["role"] if user else "user"
            session["role"] = role

        if role != "admin":
            return redirect(url_for("home.index"))
            
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("")
@admin_required
def admin_dashboard():
    """관리자 통계 대시보드 화면. (FR-55~58)"""
    
    # 7일 전(KST) 구하기 (활성 사용자 집계용)
    seven_days_ago = kst_today() - timedelta(days=7)
    # DB DATETIME과 비교하기 위해 포맷팅
    active_date_limit = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")

    with db() as cursor:
        # 1. 사용자 현황 (FR-55)
        # 1-1) 전체 가입자 수
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"] or 0

        # 1-2) 활성 사용자 수 (최근 7일 내 분석 기록이 있는 사용자)
        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id) as cnt
            FROM (
                SELECT user_id FROM delivery_records WHERE created_at >= %s
                UNION ALL
                SELECT user_id FROM time_records WHERE created_at >= %s
            ) as active_users
            """,
            (active_date_limit, active_date_limit)
        )
        active_users = cursor.fetchone()["cnt"] or 0

        # 2. 분석 통계 (FR-56)
        # 2-1) 배달 분석 건수
        cursor.execute("SELECT COUNT(*) as cnt FROM delivery_records")
        delivery_count = cursor.fetchone()["cnt"] or 0

        # 2-2) 시간 분석 건수
        cursor.execute("SELECT COUNT(*) as cnt FROM time_records")
        time_count = cursor.fetchone()["cnt"] or 0

        # 2-3) 총 배달 지출 금액
        cursor.execute("SELECT SUM(total_price) as sum_price FROM delivery_records")
        total_price = cursor.fetchone()["sum_price"] or 0

        # 2-4) 총 사용 시간 (분 단위를 시간 단위로 환산)
        cursor.execute("SELECT SUM(youtube_min + instagram_min + tiktok_min + game_min) as sum_min FROM time_records")
        total_min_res = cursor.fetchone()
        total_min = total_min_res["sum_min"] or 0
        total_hours = total_min // 60

        # 3. 도파민 점수 분포 (FR-57)
        cursor.execute(
            """
            SELECT 
                AVG(score) as avg_score,
                MAX(score) as max_score,
                MIN(score) as min_score
            FROM dopamine_scores
            """
        )
        score_stats = cursor.fetchone()
        avg_score = int(score_stats["avg_score"] or 0)
        max_score = score_stats["max_score"] or 0
        min_score = score_stats["min_score"] or 0

        # 점수 구간별 분포
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN score BETWEEN 0 AND 20 THEN 1 ELSE 0 END) as g1,
                SUM(CASE WHEN score BETWEEN 21 AND 40 THEN 1 ELSE 0 END) as g2,
                SUM(CASE WHEN score BETWEEN 41 AND 60 THEN 1 ELSE 0 END) as g3,
                SUM(CASE WHEN score BETWEEN 61 AND 80 THEN 1 ELSE 0 END) as g4,
                SUM(CASE WHEN score BETWEEN 81 AND 100 THEN 1 ELSE 0 END) as g5
            FROM dopamine_scores
            """
        )
        distribution = cursor.fetchone()
        g1 = distribution["g1"] or 0
        g2 = distribution["g2"] or 0
        g3 = distribution["g3"] or 0
        g4 = distribution["g4"] or 0
        g5 = distribution["g5"] or 0

        # 막대 그래프 높이 동적 계산 (가장 많은 구간을 90% 높이로 기준으로 삼음)
        max_cnt = max(g1, g2, g3, g4, g5, 1)
        h1 = int(g1 / max_cnt * 90)
        h2 = int(g2 / max_cnt * 90)
        h3 = int(g3 / max_cnt * 90)
        h4 = int(g4 / max_cnt * 90)
        h5 = int(g5 / max_cnt * 90)
        
        # 최저 높이 방어 (0이 아니면 최소 5%는 보이도록)
        h1 = max(5, h1) if g1 > 0 else 0
        h2 = max(5, h2) if g2 > 0 else 0
        h3 = max(5, h3) if g3 > 0 else 0
        h4 = max(5, h4) if g4 > 0 else 0
        h5 = max(5, h5) if g5 > 0 else 0

        # 4. 점수 랭킹 TOP 5 (FR-57)
        # 사용자별 역대 최고 점수를 기준으로 상위 5명을 뽑아옵니다.
        cursor.execute(
            """
            SELECT u.id as user_id, u.nickname, MAX(d.score) as top_score, u.email
            FROM dopamine_scores d
            JOIN users u ON d.user_id = u.id
            GROUP BY d.user_id, u.nickname, u.email
            ORDER BY top_score DESC
            LIMIT 5
            """
        )
        ranking_list = cursor.fetchall()
        for row in ranking_list:
            row["email"] = _mask_email(row["email"])

        # 5. 챌린지 통계 (FR-58)
        cursor.execute("SELECT COUNT(*) as total FROM user_challenges")
        challenge_total = cursor.fetchone()["total"] or 0

        cursor.execute("SELECT COUNT(*) as completed FROM user_challenges WHERE is_completed = 1")
        challenge_completed = cursor.fetchone()["completed"] or 0

        if challenge_total > 0:
            completion_rate = int(challenge_completed / challenge_total * 100)
        else:
            completion_rate = 0
            
        # 도넛 차트 SVG stroke-dashoffset 계산 (dasharray = 282.7)
        dashoffset = float(282.7 * (1 - completion_rate / 100))

    return render_template(
        "admin/index.html",
        total_users=total_users,
        active_users=active_users,
        delivery_count=delivery_count,
        time_count=time_count,
        total_price=total_price,
        total_hours=total_hours,
        avg_score=avg_score,
        max_score=max_score,
        min_score=min_score,
        h1=h1, h2=h2, h3=h3, h4=h4, h5=h5,
        g1=g1, g2=g2, g3=g3, g4=g4, g5=g5,
        ranking_list=ranking_list,
        challenge_total=challenge_total,
        challenge_completed=challenge_completed,
        completion_rate=completion_rate,
        dashoffset=dashoffset
    )


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@admin_bp.route("/users")
@admin_required
def users_list():
    """전체 가입자 목록 — 검색·필터·정렬·페이지네이션."""
    q = request.args.get("q", "").strip()
    filter_type = request.args.get("filter", "all")
    sort = request.args.get("sort", "desc")
    page = min(max(1, _safe_int(request.args.get("page", "1"), 1)), 500)

    if filter_type not in {"all", "recent", "danger", "challenge"}:
        filter_type = "all"
    if sort not in {"desc", "asc"}:
        sort = "desc"

    order_sql = "DESC" if sort == "desc" else "ASC"
    per_page = 20
    limit = page * per_page
    seven_days_ago = (kst_today() - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")

    where_parts: list[str] = []
    params: list = []

    if q:
        where_parts.append("(u.nickname LIKE %s OR u.email LIKE %s)")
        params += [f"%{q}%", f"%{q}%"]

    if filter_type == "recent":
        where_parts.append("u.created_at >= %s")
        params.append(seven_days_ago)
    elif filter_type == "danger":
        where_parts.append(
            "(SELECT score FROM dopamine_scores"
            " WHERE user_id = u.id ORDER BY week_start DESC LIMIT 1) >= 70"
        )
    elif filter_type == "challenge":
        where_parts.append(
            "EXISTS (SELECT 1 FROM user_challenges"
            " WHERE user_id = u.id AND is_completed = 0)"
        )

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    with db() as cursor:
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"] or 0

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at >= %s",
            (seven_days_ago,),
        )
        new_users = cursor.fetchone()["cnt"] or 0

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM users u WHERE"
            " (SELECT score FROM dopamine_scores"
            " WHERE user_id = u.id ORDER BY week_start DESC LIMIT 1) >= 70"
        )
        danger_users = cursor.fetchone()["cnt"] or 0

        cursor.execute(
            f"SELECT COUNT(*) as cnt FROM users u {where_sql}", tuple(params)
        )
        filtered_count = cursor.fetchone()["cnt"] or 0

        list_sql = (
            "SELECT u.id, u.nickname, u.email, u.created_at,"
            " (SELECT score FROM dopamine_scores"
            "  WHERE user_id = u.id ORDER BY week_start DESC LIMIT 1) AS latest_score,"
            " (SELECT COUNT(*) FROM delivery_records WHERE user_id = u.id) AS delivery_count,"
            " COALESCE((SELECT SUM(youtube_min + instagram_min + tiktok_min)"
            "  FROM time_records WHERE user_id = u.id), 0) AS sns_min_total,"
            " (SELECT COUNT(*) FROM user_challenges"
            "  WHERE user_id = u.id AND is_completed = 0) AS active_challenge_count,"
            " (SELECT MAX(created_at) FROM delivery_records WHERE user_id = u.id) AS last_delivery_at,"
            " (SELECT MAX(created_at) FROM time_records WHERE user_id = u.id) AS last_time_at"
            f" FROM users u {where_sql}"
            f" ORDER BY u.created_at {order_sql}"
            " LIMIT %s"
        )
        cursor.execute(list_sql, tuple(params) + (limit,))
        rows = cursor.fetchall() or []

    today = kst_today()
    for row in rows:
        ld, lt = row.get("last_delivery_at"), row.get("last_time_at")
        candidates = [x for x in [ld, lt] if x is not None]
        if candidates:
            last_act = max(candidates)
            try:
                act_date = (
                    last_act.date()
                    if isinstance(last_act, datetime)
                    else datetime.fromisoformat(str(last_act)).date()
                )
                days = (today - act_date).days
                row["last_label"] = (
                    "오늘" if days == 0 else ("어제" if days == 1 else f"{days}일 전")
                )
            except Exception:
                row["last_label"] = "기록없음"
        else:
            row["last_label"] = "기록없음"

        score = row.get("latest_score")
        if score is None:
            row["score_label"], row["score_tier"] = "기록없음", "none"
        elif score >= 70:
            row["score_label"], row["score_tier"] = f"위험 {score}점", "danger"
        elif score >= 41:
            row["score_label"], row["score_tier"] = f"보통 {score}점", "normal"
        else:
            row["score_label"], row["score_tier"] = f"안전 {score}점", "safe"

        row["sns_hours"] = round((row.get("sns_min_total") or 0) / 60, 1)
        row["email_display"] = _mask_email(row["email"])

    return render_template(
        "admin/users.html",
        users=rows,
        total_users=total_users,
        new_users=new_users,
        danger_users=danger_users,
        filtered_count=filtered_count,
        q=q,
        filter_type=filter_type,
        sort=sort,
        page=page,
        has_more=(filtered_count > limit),
    )


def _fmt_dt(raw) -> str:
    """DB DATETIME(naive) → KST 표시 문자열. 파싱 실패 시 빈 문자열."""
    try:
        if isinstance(raw, datetime):
            dt = (raw if raw.tzinfo else raw.replace(tzinfo=KST)).astimezone(KST)
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(KST)
        return dt.strftime("%Y.%m.%d %H:%M")
    except Exception:
        return ""


def _fmt_date(raw) -> str:
    """DB DATE / DATETIME → 'YYYY.MM.DD' 표시 문자열."""
    try:
        if isinstance(raw, datetime):
            return raw.strftime("%Y.%m.%d")
        return str(raw)[:10].replace("-", ".")
    except Exception:
        return ""


# ── 사용자 상세 (FR-55 확장) ─────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    """사용자 상세 — 프로필, 배달/시간 분석 내역, 도파민 점수 히스토리."""
    with db() as cursor:
        cursor.execute(
            "SELECT id, nickname, email, hourly_wage, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user:
            abort(404)
        user["created_label"] = _fmt_date(user["created_at"])
        user["email_display"] = _mask_email(user["email"])

        # 배달 분석 내역
        cursor.execute(
            "SELECT id, total_price, delivery_fee, total_calories, items, created_at"
            " FROM delivery_records WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        delivery_records = cursor.fetchall() or []
        for r in delivery_records:
            raw = r.get("items")
            if isinstance(raw, str):
                try:
                    r["items"] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    r["items"] = []
            elif not isinstance(raw, list):
                r["items"] = []
            r["date_label"] = _fmt_dt(r["created_at"])

        # 시간 분석 내역
        cursor.execute(
            "SELECT id, youtube_min, instagram_min, tiktok_min, game_min, created_at"
            " FROM time_records WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        time_records = cursor.fetchall() or []
        for r in time_records:
            total = (
                (r.get("youtube_min") or 0)
                + (r.get("instagram_min") or 0)
                + (r.get("tiktok_min") or 0)
                + (r.get("game_min") or 0)
            )
            r["total_min"] = total
            h, m = divmod(total, 60)
            r["total_label"] = f"{h}시간 {m}분" if h else f"{m}분"
            r["date_label"] = _fmt_dt(r["created_at"])

        # 도파민 점수 히스토리 (최근 8주, 오름차순)
        cursor.execute(
            "SELECT week_start, score FROM dopamine_scores"
            " WHERE user_id = %s ORDER BY week_start DESC LIMIT 8",
            (user_id,),
        )
        score_rows = list(reversed(cursor.fetchall() or []))
        for r in score_rows:
            r["week_label"] = _fmt_date(r["week_start"])[5:]  # MM.DD

    return render_template(
        "admin/user_detail.html",
        user=user,
        delivery_records=delivery_records,
        time_records=time_records,
        score_rows=score_rows,
    )


# ── 챌린지 관리 ───────────────────────────────────────────────────────────
_VALID_TARGET_TYPES = frozenset({"delivery", "time", "both"})


@admin_bp.route("/challenges")
@admin_required
def challenges_page():
    """챌린지 목록."""
    csrf_token = get_or_create_csrf_token()
    with db() as cursor:
        cursor.execute(
            "SELECT id, title, description, target_type, target_value, is_ai_generated"
            " FROM challenges ORDER BY title"
        )
        challenges = cursor.fetchall() or []
    return render_template(
        "admin/challenges.html",
        challenges=challenges,
        csrf_token=csrf_token,
    )


@admin_bp.route("/challenges", methods=["POST"])
@admin_required
def challenges_create():
    """챌린지 생성."""
    verify_csrf()
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    target_type = (request.form.get("target_type") or "").strip()
    target_value_raw = (request.form.get("target_value") or "0").strip()

    if not title or target_type not in _VALID_TARGET_TYPES:
        return redirect(url_for("admin.challenges_page"))
    try:
        target_value = max(0, int(target_value_raw))
    except ValueError:
        target_value = 0

    try:
        with db() as cursor:
            cursor.execute(
                "INSERT INTO challenges (id, title, description, target_type, target_value, is_ai_generated)"
                " VALUES (UUID(), %s, %s, %s, %s, 0)",
                (title, description, target_type, target_value),
            )
    except Exception as e:
        logger.warning("챌린지 생성 실패: %s", e)

    return redirect(url_for("admin.challenges_page"))


@admin_bp.route("/challenges/<challenge_id>/delete", methods=["POST"])
@admin_required
def challenges_delete(challenge_id: str):
    """챌린지 삭제."""
    verify_csrf()
    challenge_id = (challenge_id or "").strip()
    try:
        _uuid.UUID(challenge_id)
    except ValueError:
        abort(400)

    try:
        with db() as cursor:
            cursor.execute("DELETE FROM challenges WHERE id = %s", (challenge_id,))
    except Exception as e:
        logger.warning("챌린지 삭제 실패: %s", e)

    return redirect(url_for("admin.challenges_page"))
