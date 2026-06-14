"""홈 대시보드 라우트 테스트."""
import pytest


def test_비로그인_홈_접속_시_로그인_페이지_리다이렉트(client):
    """로그인 안 한 유저는 로그인 페이지로 리다이렉트되어야 한다."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_로그인_홈_페이지_렌더링(logged_in_client):
    """로그인 한 유저는 홈 대시보드가 정상적으로 렌더링(200 OK)되어야 한다."""
    response = logged_in_client.get("/", follow_redirects=True)
    assert response.status_code == 200
    html_content = response.data.decode("utf-8")
    assert "DopaCheck" in html_content
    assert "이번 주 도파민 점수" in html_content
