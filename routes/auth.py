"""공통 인증 — 소셜 로그인 (담당: 김승현 — FR-0, FR-0-1)."""
from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    """비로그인 사용자를 /login으로 리다이렉트하는 데코레이터. (FR-0)

    모든 도메인 라우트에 이 데코레이터를 적용한다.
    로그인 성공 시 session["user"]에 {"id": ..., "email": ..., "nickname": ...} 저장 가정.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("id"):
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
    """OAuth 콜백 — 토큰 교환 후 session["user"] 저장, users 테이블 upsert."""
    # TODO(김승현): 콜백 처리 → 로그인 성공 시 redirect(url_for("index"))
    raise NotImplementedError


@auth_bp.route("/logout")
def logout():
    """로그아웃 — 세션 정리 후 로그인 페이지로."""
    session.clear()
    return redirect(url_for("auth.login_page"))
