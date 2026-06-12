"""pytest 공통 픽스처 — 모든 테스트에서 재사용."""
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
    return client
