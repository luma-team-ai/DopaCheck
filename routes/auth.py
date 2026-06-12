"""공통 인증 — 소셜 로그인 (담당: 김승현 — FR-0, FR-0-1)."""
from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    """비로그인 사용자를 /login으로 리다이렉트하는 데코레이터. (FR-0)

    모든 도메인 라우트에 이 데코레이터를 적용한다.
    평면 세션 패턴(#21): 로그인 성공 시 session에
    user_id(BIGINT PK)·email·nickname 을 평면 키로 저장한다.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.route("/login")
def login_page():
    """소셜 로그인 페이지. (FR-0-1)"""
    return render_template("login.html")


@auth_bp.route("/auth/<provider>")
def oauth_start(provider: str):
    """Google/Kakao OAuth 시작 — Supabase Auth로 리다이렉트.

    provider: "google" | "kakao"
    """
    # TODO(김승현): Supabase Auth OAuth URL 생성 후 리다이렉트
    raise NotImplementedError


@auth_bp.route("/auth/callback")
def oauth_callback():
    """OAuth 콜백 — 토큰 교환 후 평면 세션(user_id 등) 저장, users 테이블 email 기준 upsert.

    저장 형태(평면): session["user_id"]=<BIGINT PK>, session["email"], session["nickname"].
    """
    # TODO(#16, 김승현): 콜백 처리 → users upsert(email 기준) → session 평면 저장 → redirect(index)
    raise NotImplementedError


@auth_bp.route("/logout")
def logout():
    """로그아웃 — 세션 정리 후 로그인 페이지로."""
    session.clear()
    return redirect(url_for("auth.login_page"))
