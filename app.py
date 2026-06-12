# app.py
from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# OAuth 초기화
from routes.auth import auth_bp, init_oauth
init_oauth(app)
app.register_blueprint(auth_bp)

# 각 메뉴 Blueprint 등록
from routes.delivery  import delivery_bp
from routes.time      import time_bp
from routes.report    import report_bp
from routes.history   import history_bp
from routes.score     import score_bp
from routes.challenge import challenge_bp

app.register_blueprint(delivery_bp)
app.register_blueprint(time_bp)
app.register_blueprint(report_bp)
app.register_blueprint(history_bp)
app.register_blueprint(score_bp)
app.register_blueprint(challenge_bp)


@app.route("/")
def index():
    """홈 — 로그인 상태면 리포트로, 아니면 로그인으로 리다이렉트. (FR-0)"""
    from flask import session, redirect, url_for
    if session.get("user_id"):
        return redirect(url_for("report.report_page"))
    return redirect(url_for("auth.login_page"))  # P3: url_for로 통일


if __name__ == "__main__":
    app.run(debug=True)