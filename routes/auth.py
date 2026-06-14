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

    # P2: 대괄호 접근(os.environ[key]) 대신 명시적 RuntimeError —
    # 환경변수 미설정 시 KeyError 대신 원인이 명확한 메시지로 앱 시작을 막는다.
    def _require_env(key: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(
                f"{key} 환경변수가 설정되지 않았습니다. "
                f".env.example 참고 후 .env에 설정하세요."
            )
        return val

    oauth.register(
        name="google",
        client_id=_require_env("GOOGLE_CLIENT_ID"),
        client_secret=_require_env("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )

    oauth.register(
        name="kakao",
        client_id=_require_env("KAKAO_CLIENT_ID"),
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


@auth_bp.route("/auth/dev_login")
def dev_login():
    """로컬 개발 검증을 위한 더미 로그인 라우트."""
    if os.environ.get("FLASK_ENV") == "development":
        user_id = upsert_user_profile(
            email="dev_test@example.com",
            nickname="대표님테스터",
            provider="dev",
            provider_id="dev_test"
        )
        session["user_id"] = user_id
        session["nickname"] = "대표님테스터"
        session["email"] = "dev_test@example.com"
        return redirect("/")
    return "Not Allowed in Production", 403


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
    from authlib.integrations.base_client import OAuthError
    # P2: kakao_callback과 동일하게 OAuthError를 catch — state 불일치·코드 만료 시 500 노출 방지.
    try:
        token = oauth.google.authorize_access_token()
    except OAuthError as e:
        # P2: OAuthError 원문(내부 엔드포인트·클라이언트ID 힌트 등 포함 가능)을 사용자에게 직접 노출 금지.
        # 상세 오류는 서버 로그에만 기록, 사용자에게는 고정 문자열만 반환.
        logger.warning("Google 토큰 교환 실패 [%s]: %s", type(e).__name__, e)
        return "로그인 중 오류가 발생했습니다. 다시 시도해주세요.", 401

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
    # P3: google_login과 동일하게 or 패턴으로 통일 — os.environ.get(key, default)는
    # default 인자가 항상 평가되어 url_for()가 불필요하게 호출되는 문제 있음.
    redirect_uri = os.environ.get("KAKAO_REDIRECT_URI") or url_for("auth.kakao_callback", _external=True)
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
        # P2: OAuthError 원문을 사용자에게 직접 노출 금지 — 상세 오류는 서버 로그에만 기록.
        logger.warning("Kakao 토큰 교환 실패 [%s]: %s", type(e).__name__, e)
        return "로그인 중 오류가 발생했습니다. 다시 시도해주세요.", 401
    if not token or not token.get("access_token"):
        return "카카오 인증 실패: 액세스 토큰을 수신하지 못했습니다.", 401

    # P2: user/me 응답 유효성 체크 — 네트워크 오류·비정상 응답 시 500 대신 401 반환.
    resp = oauth.kakao.get("user/me")
    if not resp.ok:
        logger.warning("Kakao user/me 요청 실패: status=%s", resp.status_code)
        return "카카오 사용자 정보 조회 실패. 다시 시도해주세요.", 401
    profile = resp.json()

    # P2: profile['id'] KeyError 방어 — id 없으면 401 반환.
    # account_email 스코프를 요청하지 않으므로 고유 식별자를 email 컬럼에 저장
    # users.email은 UNIQUE — 닉네임은 중복 가능하므로 kakao_{id} 형태로 고유값 사용
    raw_id = profile.get("id")
    if not raw_id:
        logger.warning("Kakao profile에 id 필드 없음: %s", list(profile.keys()))
        return "카카오 사용자 식별자를 가져오지 못했습니다.", 401
    kakao_id = str(raw_id)
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
        provider_id = kakao_id
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