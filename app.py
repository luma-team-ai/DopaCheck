"""Dopamine Check — Flask 앱 진입점.

각 도메인 라우트는 routes/ 패키지의 Blueprint로 분리되어 있다.
담당자는 자신의 Blueprint 파일만 수정한다. (app.py 공통 수정은 팀 합의 후)
"""
import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, session, url_for

load_dotenv()

from routes.auth import auth_bp, init_oauth
from routes.challenge import challenge_bp
from routes.delivery import delivery_bp
from routes.history import history_bp
from routes.home import home_bp
from routes.report import report_bp
from routes.score import score_bp
from routes.time import time_bp

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB — 대용량 업로드 OOM 방지 (#36)

# 세션 쿠키 보안 속성 (#44) — CSRF 방어 깊이 강화
# - HTTPONLY: JS에서 쿠키 접근 차단 (XSS 토큰 탈취 방지)
# - SAMESITE=Lax: 크로스사이트 POST에 쿠키 미전송 (CSRF 1차 방어)
# - SECURE: 운영(HTTPS)에서만 쿠키 전송. 개발(http://localhost)에선 False라야 로그인 유지됨
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"

# 환경 분기: FLASK_ENV=production(CloudType 배포)일 때만 ProxyFix 적용.
# - production: Nginx 리버스 프록시가 있으므로 X-Forwarded-Proto를 신뢰 → https:// URL 생성.
# - development: 직접 실행이므로 ProxyFix 불필요, http://localhost 그대로 유지.
if os.environ.get("FLASK_ENV") == "production":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# OAuth 초기화 (Google/Kakao 소셜 로그인)
init_oauth(app)

app.register_blueprint(home_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(delivery_bp)
app.register_blueprint(time_bp)
app.register_blueprint(report_bp)
app.register_blueprint(history_bp)
app.register_blueprint(score_bp)
app.register_blueprint(challenge_bp)

# P1 수정: dev_login은 FLASK_ENV=development일 때만 등록 (운영 오인 설정 시 이중 방어)
if os.environ.get("FLASK_ENV") == "development":
    from routes.dev_only import dev_bp
    app.register_blueprint(dev_bp)


@app.route("/")
def index():
    """홈 — 로그인 상태면 홈 대시보드로, 아니면 로그인으로 리다이렉트. (FR-0)"""
    if session.get("user_id"):
        return redirect(url_for("home.index"))
    return redirect(url_for("auth.login_page"))


@app.errorhandler(413)
def handle_request_entity_too_large(error):
    """업로드 크기가 MAX_CONTENT_LENGTH(5MB)를 초과하면 flash 후 /delivery로 리다이렉트. (#43)

    전용 핸들러가 없으면 기본 HTML 에러 페이지가 노출되어 flash+redirect 흐름이 끊긴다.
    """
    flash("파일 크기가 5MB를 초과했습니다.", "error")
    return redirect(url_for("delivery.delivery_page"))

if __name__ == "__main__":
    # 디버그 모드는 환경변수로 게이트 — 운영에서 debug=True 노출 방지 (#44 P3)
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000)
