"""주차/날짜 경계 공통 유틸 (KST 기준) — #11 전역 타임존 통일.

created_at / week_start 를 다루는 모든 도메인(report·score·history·delivery·time)이
이 모듈을 사용해 타임존·주 경계 처리를 통일한다.

설계 의도:
- 서버 타임존(Cloudtype 컨테이너는 보통 UTC)과 무관하게 **KST 기준**으로 주차를 계산한다.
- created_at(timestamptz) 비교 시 타임존 누락(하루 오차)과 초 단위 경계 누락(밀리초)을 방지하기 위해
  [시작, 익일) exclusive 경계 + 명시적 +09:00 오프셋을 사용한다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))   # 한국 표준시 (DST 없음)


def week_bounds(ref: date) -> tuple[str, str]:
    """ref가 속한 주(월~일)의 시작일(월요일)·종료일(일요일) ISO 문자열을 반환한다."""
    start = ref - timedelta(days=ref.weekday())   # 월요일
    end = start + timedelta(days=6)               # 일요일
    return start.isoformat(), end.isoformat()


def get_week_ranges() -> tuple[tuple[str, str], tuple[str, str]]:
    """(이번 주 범위, 저번 주 범위) — 각 (start_iso, end_iso) 튜플. KST 기준."""
    today = datetime.now(KST).date()
    return week_bounds(today), week_bounds(today - timedelta(weeks=1))


def kst_bounds(week_start: str, week_end: str) -> tuple[str, str]:
    """주 범위를 KST 타임존이 명시된 [시작, 익일) 경계 문자열로 변환한다.

    Returns:
        (gte_at, lt_at) — created_at 필터에 `.gte(gte_at).lt(lt_at)` 형태로 사용.
        예: ("2026-06-08T00:00:00+09:00", "2026-06-15T00:00:00+09:00")
    """
    next_day = (date.fromisoformat(week_end) + timedelta(days=1)).isoformat()
    return f"{week_start}T00:00:00+09:00", f"{next_day}T00:00:00+09:00"
