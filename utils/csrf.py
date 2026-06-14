"""CSRF 토큰 생성·검증 유틸리티."""
import hmac
import secrets

from flask import abort, request, session

_CSRF_SESSION_KEY = "csrf_token"


def get_or_create_csrf_token() -> str:
    """세션에서 CSRF 토큰을 읽거나, 없으면 생성해 저장 후 반환한다."""
    if _CSRF_SESSION_KEY not in session:
        session[_CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[_CSRF_SESSION_KEY]


def verify_csrf() -> None:
    """요청 헤더(X-CSRF-Token) 또는 폼 필드(csrf_token)의 CSRF 토큰을 검증한다.

    타이밍 공격 방지를 위해 hmac.compare_digest 사용.
    불일치 시 abort(403).
    """
    expected = session.get(_CSRF_SESSION_KEY)
    if not expected:
        abort(403)
    received = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token")
        or ""
    )
    if not hmac.compare_digest(str(expected), str(received)):
        abort(403)
