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
        # client_secret을 ""(빈 문자열)로 두면 authlib이 값이 있다고 판단해
        # 토큰 요청 시 client_secret= 파라미터를 전송 → 카카오가 invalid_client 반환.
        # None으로 설정해야 authlib이 자격증명 전송 자체를 완전히 생략한다.
        client_secret=os.environ.get("KAKAO_CLIENT_SECRET") or None,
        authorize_url="https://kauth.kakao.com/oauth/authorize",
        access_token_url="https://kauth.kakao.com/oauth/token",
        api_base_url="https://kapi.kakao.com/v2/",
        client_kwargs={
            "scope": "profile_nickname",  # account_email 제거 — 이메일 동의 불필요
            # client_secret이 None이어도 authlib이 Basic Auth를 시도할 수 있으므로
            # token_endpoint_auth_method를 "none"으로 명시해 이중으로 차단한다.
            "token_endpoint_auth_method": "none",
        }
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
    # GOOGLE_REDIRECT_URI 환경변수가 있으면 최우선 사용 (CloudType 배포 환경).
    # 없으면 url_for()로 동적 생성 (로컬 개발 환경 fallback).
    # ProxyFix와 이중 방어 구조로 http/https 불일치 문제를 완전히 차단한다.
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI") or url_for("auth.google_callback", _external=True)
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
    from authlib.integrations.base_client import OAuthError
    # authlib은 Flask request context에서 redirect_uri를 자동 추출한다.
    # authorize_access_token()에 redirect_uri를 명시적으로 넘기면
    # 내부 fetch_access_token()에도 동일 인자가 전달되어
    # "got multiple values for keyword argument 'redirect_uri'" TypeError 발생.
    # → 인자 없이 호출하는 것이 올바른 방법.
    try:
        token = oauth.kakao.authorize_access_token()
    except OAuthError as e:
        logger.warning("Kakao 토큰 교환 실패 [%s]: %s", type(e).__name__, e)
        return f"카카오 로그인 실패: {e}. 다시 시도해주세요.", 401
    if not token or not token.get("access_token"):
        return "카카오 인증 실패: 액세스 토큰을 수신하지 못했습니다.", 401

    resp = oauth.kakao.get("user/me")
    profile = resp.json()

    # account_email 스코프를 요청하지 않으므로 고유 식별자를 email 컬럼에 저장
    # users.email은 UNIQUE — 닉네임은 중복 가능하므로 kakao_{id} 형태로 고유값 사용
    kakao_id = str(profile["id"])
    nickname = (
        profile.get("kakao_account", {}).get("profile", {}).get("nickname")
        or profile.get("properties", {}).get("nickname")
        or f"카카오유저{kakao_id[-4:]}"  # 닉네임도 없는 경우 fallback
    )
    email = f"kakao_{kakao_id}"  # UNIQUE 보장 + 이메일 동의 불필요

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
def login_required(view):
    """모든 도메인 라우트에 이 데코레이터를 적용한다.
    평면 세션 패턴(#21): 로그인 성공 시 session에
    user_id(BIGINT PK)·email·nickname 을 평면 키로 저장한다.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)
    return wrapped