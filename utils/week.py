"""주차/날짜 경계 공통 유틸 (KST 기준) — #11 전역 타임존 통일.

created_at / week_start 를 다루는 모든 도메인(report·score·history·delivery·time)이
이 모듈을 사용해 타임존·주 경계 처리를 통일한다.

설계 의도:
- 서버 타임존(컨테이너는 보통 UTC)과 무관하게 **KST 기준**으로 주차를 계산한다.
- MariaDB 전환(#21): created_at 비교의 타임존은 db.client에서 세션 TZ를 +09:00으로
  고정해 일원화한다(created_at·경계 모두 KST-naive). 경계 문자열은 오프셋 없는
  DATETIME 리터럴이며, 하루 오차/초 단위 누락 방지를 위해 [시작, 익일) exclusive 경계를 쓴다.
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
    """주 범위를 MariaDB DATETIME(KST) 비교용 [시작, 익일) 경계 문자열로 변환한다.

    DB 세션 타임존은 db.client에서 +09:00으로 고정되므로(created_at도 KST-naive),
    경계도 오프셋 없는 KST-naive DATETIME 리터럴(공백 구분)로 맞춘다.
    오프셋(+09:00)이나 'T' 구분자를 넣으면 MariaDB가 DATETIME 비교 시 변환에 실패해
    해당 주 레코드가 0건으로 조용히 누락되므로 사용하지 않는다.

    Returns:
        (gte_at, lt_at) — `created_at >= %s AND created_at < %s` 형태로 바인딩해 사용.
        예: ("2026-06-08 00:00:00", "2026-06-15 00:00:00")
    """
    next_day = (date.fromisoformat(week_end) + timedelta(days=1)).isoformat()
    return f"{week_start} 00:00:00", f"{next_day} 00:00:00"
