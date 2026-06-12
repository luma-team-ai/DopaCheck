"""Dopamine Check — Flask 앱 진입점.

각 도메인 라우트는 routes/ 패키지의 Blueprint로 분리되어 있다.
담당자는 자신의 Blueprint 파일만 수정한다. (app.py 공통 수정은 팀 합의 후)
"""
import os

from dotenv import load_dotenv
from flask import Flask, redirect, session, url_for

load_dotenv()

from routes.auth import auth_bp, init_oauth
from routes.challenge import challenge_bp
from routes.delivery import delivery_bp
from routes.history import history_bp
from routes.report import report_bp
from routes.score import score_bp
from routes.time import time_bp

app = Flask(__name__)
# TODO(#14): 공개 기본값 fallback은 세션 위조 위험 — 운영 시 FLASK_SECRET_KEY 필수화(별도 PR).
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

# OAuth 초기화 (Google/Kakao 소셜 로그인)
init_oauth(app)

app.register_blueprint(auth_bp)
app.register_blueprint(delivery_bp)
app.register_blueprint(time_bp)
app.register_blueprint(report_bp)
app.register_blueprint(history_bp)
app.register_blueprint(score_bp)
app.register_blueprint(challenge_bp)


@app.route("/")
def index():
    """홈 — 로그인 상태면 리포트로, 아니면 로그인으로 리다이렉트. (FR-0)"""
    if session.get("user_id"):
        return redirect(url_for("report.report_page"))
    return redirect(url_for("auth.login_page"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
