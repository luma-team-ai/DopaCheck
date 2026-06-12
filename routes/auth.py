# routes/auth.py
import logging
from flask import Blueprint, redirect, render_template, request, session, url_for
from authlib.integrations.flask_client import OAuth
from db.client import upsert_user_profile
from functools import wraps
import os

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_oauth(app):
    """app.py에서 호출해 OAuth 초기화"""
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )

    oauth.register(
        name="kakao",
        client_id=os.environ["KAKAO_CLIENT_ID"],
        client_secret=os.environ.get("KAKAO_CLIENT_SECRET", ""),  # Kakao REST API는 secret 없이도 동작
        authorize_url="https://kauth.kakao.com/oauth/authorize",
        access_token_url="https://kauth.kakao.com/oauth/token",
        api_base_url="https://kapi.kakao.com/v2/",
        client_kwargs={"scope": "profile_nickname account_email"}
    )


# ── 로그인 페이지 ──────────────────────────────────────────
@auth_bp.route("/login")
def login_page():
    """소셜 로그인 페이지. (FR-0-1)"""
    if session.get("user_id"):
        return redirect("/")
    return render_template("login.html")


# ── Google 로그인 ──────────────────────────────────────────
@auth_bp.route("/auth/google")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    # P2: userinfo가 None일 경우 (openid 스코프 응답 누락) 방어
    user_info = token.get("userinfo")
    if not user_info or not user_info.get("email"):
        return "Google 로그인 실패: 사용자 정보를 받아오지 못했습니다.", 401

    user_id = upsert_user_profile(
        email       = user_info["email"],
        nickname    = user_info.get("name") or user_info["email"].split("@")[0],
        provider    = "google",
        provider_id = user_info["sub"]
    )

    session["user_id"]  = user_id
    session["nickname"] = user_info.get("name") or user_info["email"].split("@")[0]
    session["email"]    = user_info["email"]
    return redirect("/")


# ── Kakao 로그인 ──────────────────────────────────────────
@auth_bp.route("/auth/kakao")
def kakao_login():
    # .env의 KAKAO_REDIRECT_URI: http://localhost:5000/oauth2/code/kakao
    redirect_uri = os.environ.get("KAKAO_REDIRECT_URI", url_for("auth.kakao_callback", _external=True))
    return oauth.kakao.authorize_redirect(redirect_uri)


@auth_bp.route("/oauth2/code/kakao")  # .env의 KAKAO_REDIRECT_URI와 일치
def kakao_callback():
    # P2: 토큰 교환 실패 시 OAuthError가 일어나도 예외 처리 없이 진행되는 문제 방지
    from authlib.integrations.base_client import OAuthError
    try:
        token = oauth.kakao.authorize_access_token()
    except OAuthError as e:
        logger.warning("Kakao 토큰 교환 실패: %s", e)
        return "카카오 로그인 실패했습니다. 다시 시도해주세요.", 401
    if not token or not token.get("access_token"):
        return "카카오 인증 실패: 액세스 토큰을 수신하지 못했습니다.", 401
    resp = oauth.kakao.get("user/me")
    profile = resp.json()

    kakao_account = profile.get("kakao_account", {})
    email    = kakao_account.get("email", f"kakao_{profile['id']}@kakao.com")
    nickname = kakao_account.get("profile", {}).get("nickname") or email.split("@")[0]

    user_id = upsert_user_profile(
        email       = email,
        nickname    = nickname,
        provider    = "kakao",
        provider_id = str(profile["id"])
    )

    session["user_id"]  = user_id
    session["nickname"] = nickname
    session["email"]    = email
    return redirect("/")


# ── 로그아웃 ──────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))  # P3: url_for로 통일


# ── 로그인 필수 데코레이터 ────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated