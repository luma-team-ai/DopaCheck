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
    """로그인 상태 클라이언트 — session["user"]를 더미로 주입."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "test@example.com",
            "nickname": "테스트",
        }
    return client
