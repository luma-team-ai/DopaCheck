"""로컬 개발 전용 더미 로그인 라우트.

P1 수정: 운영 환경에 인증 우회 라우트가 노출되는 것을 막기 위해
auth.py(프로덕션 라우트)에서 분리했다. app.py는 FLASK_ENV=development일
때만 이 블루프린트를 등록하며, 라우트 자체도 로컬호스트 요청만 허용하는
이중 가드를 둔다.
"""
import os
from flask import Blueprint, redirect, request, session
from db.client import upsert_user_profile

dev_bp = Blueprint("dev_only", __name__)


@dev_bp.route("/auth/dev_login")
def dev_login():
    """로컬 개발 검증을 위한 더미 로그인 라우트."""
    if os.environ.get("FLASK_ENV") != "development" or request.remote_addr not in ("127.0.0.1", "::1"):
        return "Not Allowed in Production", 403

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
