"""종합 리포트 + SNS 공유 카드 (담당: 정재봉 — FR-16~20)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, abort, render_template, session

from ai import comment
from db.client import get_supabase
from routes.auth import login_required

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__, url_prefix="/report")

KST = timezone(timedelta(hours=9))   # 한국 표준시 (DST 없음) — 주차 경계 기준


# ── 주차 계산 헬퍼 ────────────────────────────────────────────────────────────

def _week_bounds(ref: date) -> tuple[str, str]:
    """ref가 속한 주(월~일)의 시작일(월요일)과 종료일(일요일) ISO 문자열을 반환한다."""
    start = ref - timedelta(days=ref.weekday())   # 월요일
    end = start + timedelta(days=6)               # 일요일
    return start.isoformat(), end.isoformat()


def get_week_ranges() -> tuple[tuple[str, str], tuple[str, str]]:
    """(이번 주 범위, 저번 주 범위) — 각 (start_iso, end_iso) 튜플. KST 기준."""
    today = datetime.now(KST).date()
    this_week = _week_bounds(today)
    last_week = _week_bounds(today - timedelta(weeks=1))
    return this_week, last_week


# ── 순수 집계 함수 (DB 없이 단위 테스트 가능) ─────────────────────────────────

def aggregate_delivery(rows: list[dict]) -> dict:
    """delivery_records 행 목록을 받아 주간 집계 dict를 반환한다.

    Returns:
        {
            "total_price": int,       # 총 지출 (원)
            "total_calories": int,    # 총 칼로리 (kcal)
            "count": int,             # 주문 건수
        }
    """
    total_price = sum(r.get("total_price") or 0 for r in rows)
    total_calories = sum(r.get("total_calories") or 0 for r in rows)
    return {
        "total_price": total_price,
        "total_calories": total_calories,
        "count": len(rows),
    }


def aggregate_time(rows: list[dict]) -> dict:
    """time_records 행 목록을 받아 주간 집계 dict를 반환한다.

    Returns:
        {
            "youtube_min": int,
            "instagram_min": int,
            "tiktok_min": int,
            "game_min": int,
            "total_min": int,         # 전체 합계 (분)
        }
    """
    youtube = sum(r.get("youtube_min") or 0 for r in rows)
    instagram = sum(r.get("instagram_min") or 0 for r in rows)
    tiktok = sum(r.get("tiktok_min") or 0 for r in rows)
    game = sum(r.get("game_min") or 0 for r in rows)
    return {
        "youtube_min": youtube,
        "instagram_min": instagram,
        "tiktok_min": tiktok,
        "game_min": game,
        "total_min": youtube + instagram + tiktok + game,
    }


def clamp_score(value) -> int:
    """도파민 점수를 0~100 범위로 강제한다 (CSS conic-gradient/차트 깨짐 방지)."""
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


# ── DB 조회 헬퍼 ──────────────────────────────────────────────────────────────

def _kst_bounds(week_start: str, week_end: str) -> tuple[str, str]:
    """주 범위를 KST 타임존이 명시된 [시작, 익일) 경계 문자열로 변환한다.

    created_at(timestamptz) 비교 시 ① 타임존 누락으로 인한 하루 오차,
    ② 초 단위 lte 경계의 밀리초 누락을 방지한다 (익일 00:00 미만 exclusive).
    """
    next_day = (date.fromisoformat(week_end) + timedelta(days=1)).isoformat()
    return f"{week_start}T00:00:00+09:00", f"{next_day}T00:00:00+09:00"


def _fetch_delivery(user_id: str, week_start: str, week_end: str) -> list[dict]:
    """해당 주의 delivery_records를 조회한다.

    DB 오류 시 빈 리스트를 반환한다(의도적 폴백 설계).
    UI에서 '기록 없음'과 구분이 필요하면 report_page의 db_error 컨텍스트를 활용하라.
    """
    try:
        gte_at, lt_at = _kst_bounds(week_start, week_end)
        supabase = get_supabase()
        result = (
            supabase.table("delivery_records")
            .select("total_price, total_calories")
            .eq("user_id", user_id)
            .gte("created_at", gte_at)
            .lt("created_at", lt_at)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning("delivery_records 조회 실패: %s", exc)
        return []


def _fetch_time(user_id: str, week_start: str, week_end: str) -> list[dict]:
    """해당 주의 time_records를 조회한다.

    DB 오류 시 빈 리스트를 반환한다(의도적 폴백 설계).
    """
    try:
        gte_at, lt_at = _kst_bounds(week_start, week_end)
        supabase = get_supabase()
        result = (
            supabase.table("time_records")
            .select("youtube_min, instagram_min, tiktok_min, game_min")
            .eq("user_id", user_id)
            .gte("created_at", gte_at)
            .lt("created_at", lt_at)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning("time_records 조회 실패: %s", exc)
        return []


def _fetch_score(user_id: str, week_start: str) -> dict:
    """해당 주의 dopamine_scores를 조회한다. 없거나 실패 시 0 dict 반환."""
    empty = {
        "score": 0,
        "delivery_contribution": 0,
        "time_contribution": 0,
        "challenge_bonus": 0,
    }
    try:
        supabase = get_supabase()
        result = (
            supabase.table("dopamine_scores")
            .select("score, delivery_contribution, time_contribution, challenge_bonus")
            .eq("user_id", user_id)
            .eq("week_start", week_start)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            row["score"] = clamp_score(row.get("score"))
            # CSS width(%)로 직접 사용되므로 0~100 클램핑 필수
            row["delivery_contribution"] = clamp_score(row.get("delivery_contribution"))
            row["time_contribution"] = clamp_score(row.get("time_contribution"))
            row["challenge_bonus"] = clamp_score(row.get("challenge_bonus"))
            return row
        return empty
    except Exception as exc:
        logger.warning("dopamine_scores 조회 실패: %s", exc)
        return empty


# ── 라우트 ────────────────────────────────────────────────────────────────────

@report_bp.route("")
@login_required
def report_page():
    """배달 지출·시간 소비 통합 대시보드.

    1. delivery_records + time_records 주간 집계 조회 (FR-16)
    2. 도파민 점수 표시 (FR-18)
    3. ai.comment.generate("report", context) — 종합 인사이트 (FR-17)
    4. 저번 주 vs 이번 주 비교 차트 데이터 (FR-20)
    5. 공유 카드 영역 → html2canvas로 이미지 저장/SNS 공유 (FR-19, 클라이언트 측)
    """
    # login_required가 session["user"] 존재를 보장하지만, id 키 누락 시 401 처리
    user = session.get("user") or {}
    user_id: str | None = user.get("id")
    if not user_id:
        abort(401)

    # ── 주차 범위 계산 ────────────────────────────────────────
    this_week_range, last_week_range = get_week_ranges()
    this_start, this_end = this_week_range
    last_start, last_end = last_week_range

    # ── 이번 주 데이터 집계 ───────────────────────────────────
    # fetch 함수는 DB 오류 시 빈값을 반환(의도적 폴백 설계 — 각 함수 docstring 참조).
    # '데이터 없음'과 'DB 오류'는 logger.warning으로 구분하며, 운영 중 로그를 모니터링할 것.
    this_delivery = aggregate_delivery(_fetch_delivery(user_id, this_start, this_end))
    this_time = aggregate_time(_fetch_time(user_id, this_start, this_end))
    this_score = _fetch_score(user_id, this_start)

    # ── 저번 주 데이터 집계 ───────────────────────────────────
    last_delivery = aggregate_delivery(_fetch_delivery(user_id, last_start, last_end))
    last_time = aggregate_time(_fetch_time(user_id, last_start, last_end))
    last_score = _fetch_score(user_id, last_start)

    # ── AI 종합 인사이트 (FR-17) ─────────────────────────────
    ai_comment = _generate_ai_comment(this_delivery, this_time, this_score)

    return render_template(
        "report/index.html",
        # 이번 주
        this_delivery=this_delivery,
        this_time=this_time,
        this_score=this_score,
        this_week_start=this_start,
        # 저번 주
        last_delivery=last_delivery,
        last_time=last_time,
        last_score=last_score,
        last_week_start=last_start,
        # AI 인사이트
        ai_comment=ai_comment,
        # 유저 닉네임
        nickname=session["user"].get("nickname", ""),
    )


def _generate_ai_comment(
    delivery: dict, time: dict, score: dict
) -> str:
    """ai.comment.generate 호출. 실패(NotImplementedError 포함) 시 fallback 반환. (FR-45)"""
    context = {
        "total_price": delivery["total_price"],
        "total_calories": delivery["total_calories"],
        "delivery_count": delivery["count"],
        "total_time_min": time["total_min"],
        "youtube_min": time["youtube_min"],
        "instagram_min": time["instagram_min"],
        "tiktok_min": time["tiktok_min"],
        "game_min": time["game_min"],
        "score": score["score"],
    }
    try:
        return comment.generate("report", context)
    except NotImplementedError:
        logger.info("ai.comment.generate 미구현 — fallback 사용")
    except Exception as exc:
        logger.warning("ai.comment.generate 호출 실패: %s", exc)

    # fallback: 데이터 기반 간단 메시지
    price = delivery["total_price"]
    mins = time["total_min"]
    if price == 0 and mins == 0:
        return "이번 주는 아직 기록이 없어요. 배달 분석이나 시간 분석을 먼저 해보세요! 🌱"
    parts = []
    if price > 0:
        parts.append(f"이번 주 배달에 {price:,}원을 사용했어요")
    if mins > 0:
        parts.append(f"SNS·게임에 {mins // 60}시간 {mins % 60}분을 보냈어요")
    return ". ".join(parts) + ". 조금씩 줄여가는 것도 좋은 시작이에요! 💪"
