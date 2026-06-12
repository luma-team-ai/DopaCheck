"""인증 테스트 (담당: 김승현)."""
import pytest


def test_비로그인_접근시_로그인으로_리다이렉트(client):
    """FR-0: 비로그인 사용자는 모든 페이지에서 /login으로 리다이렉트."""
    for path in ["/delivery", "/time", "/report", "/history", "/score", "/challenge"]:
        res = client.get(path)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]


def test_로그인_페이지_접근가능(client):
    assert client.get("/login").status_code == 200


@pytest.mark.skip(reason="TODO(김승현): OAuth 콜백 구현 후 작성")
def test_oauth_콜백():
    ...
