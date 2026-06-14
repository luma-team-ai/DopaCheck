"""pytest 공통 픽스처 — 모든 테스트에서 재사용."""
import os

# OAuth 클라이언트는 app import 시점(init_oauth)에 GOOGLE/KAKAO 키를 필수로 읽는다.
# 로컬은 .env가 제공하지만 CI·새 클론엔 .env가 없어 import 자체가 RuntimeError로 깨진다.
# app import 전에 더미값을 주입해 테스트가 키 없이도 수집되게 한다.
# setdefault: 실제 환경에 값이 있으면(쉘 export·CI 시크릿) 그대로 보존한다.
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("KAKAO_CLIENT_ID", "test-kakao-client-id")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key-for-pytest")

import pytest

from app import app as flask_app


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """로그인 상태 클라이언트 — 평면 세션(user_id 등)을 더미로 주입(#21)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1            # BIGINT PK
        sess["email"] = "test@example.com"
        sess["nickname"] = "테스트"
        sess["csrf_token"] = "test-csrf-token"
    return client
