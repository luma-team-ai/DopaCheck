"""커넥션 풀 단위 테스트 (#23, #71).

실제 네트워크 접속 없이 _get_pool() 싱글톤 동작과
PooledDB 생성 인자를 검증한다.

#71 추가: bounded-timeout / PoolExhaustedError 동작 검증.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# --------------------------------------------------------------------------- #
# Fixture: 매 테스트 전후 _pool 싱글톤 초기화 (다른 테스트 오염 방지)
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_pool():
    """각 테스트 전후에 db.client._pool을 None으로 초기화한다.

    _pool이 mock 객체로 남으면 이후 테스트(report 등)가 실제 DB 대신
    MagicMock에서 커넥션을 받아 TypeError를 일으키므로 반드시 정리해야 한다.
    """
    import db.client as client_mod
    client_mod._pool = None
    yield
    client_mod._pool = None


# --------------------------------------------------------------------------- #
# 헬퍼
# --------------------------------------------------------------------------- #

def _get_client():
    """db.client 모듈 참조를 반환한다(_pool은 fixture가 초기화)."""
    import db.client as client_mod
    return client_mod


def _db_env():
    """테스트용 최소 DB 환경변수 딕셔너리."""
    return {
        "DB_HOST": "test-host",
        "DB_PORT": "3306",
        "DB_USER": "test-user",
        "DB_PASSWORD": "test-pass",
        "DB_NAME": "test-db",
    }


# --------------------------------------------------------------------------- #
# 테스트: _get_pool() 싱글톤
# --------------------------------------------------------------------------- #

class TestGetPoolSingleton:
    """_get_pool()이 싱글톤을 반환하는지 검증."""

    def test_returns_same_object_on_two_calls(self):
        """_get_pool() 두 번 호출 시 동일 객체를 반환해야 한다."""
        mock_pool = MagicMock()
        client = _get_client()

        with patch.dict(os.environ, _db_env()):
            with patch("db.client.PooledDB", return_value=mock_pool) as mock_cls:
                pool1 = client._get_pool()
                pool2 = client._get_pool()

        assert pool1 is pool2, "_get_pool()이 두 번 호출에서 서로 다른 객체를 반환했다"
        assert mock_cls.call_count == 1, f"PooledDB가 {mock_cls.call_count}번 생성됐다 (기대: 1)"

    def test_pool_is_none_before_first_call(self):
        """모듈 _pool 변수가 None으로 시작해야 한다(import 시 미접속 보장)."""
        client = _get_client()
        assert client._pool is None


# --------------------------------------------------------------------------- #
# 테스트: PooledDB 생성 인자
# --------------------------------------------------------------------------- #

class TestPooledDBArgs:
    """PooledDB가 올바른 인자로 생성되는지 검증."""

    def _call_get_pool(self, extra_env: dict | None = None):
        """_get_pool()을 호출하고 PooledDB mock과 호출 kwargs를 반환한다."""
        mock_pool = MagicMock()
        client = _get_client()
        env = {**_db_env(), **(extra_env or {})}

        with patch.dict(os.environ, env, clear=False):
            with patch("db.client.PooledDB", return_value=mock_pool) as mock_cls:
                client._get_pool()

        assert mock_cls.call_count == 1
        _, kwargs = mock_cls.call_args
        return mock_cls, kwargs

    def test_creator_is_pymysql(self):
        import pymysql as pymysql_mod
        _, kwargs = self._call_get_pool()
        assert kwargs["creator"] is pymysql_mod

    def test_blocking_is_false(self):
        """blocking=False 로 변경 — 풀 소진 시 무한 대기 대신 TooManyConnections 즉시 발생 (#71)."""
        _, kwargs = self._call_get_pool()
        assert kwargs["blocking"] is False

    def test_ping_is_4(self):
        _, kwargs = self._call_get_pool()
        assert kwargs["ping"] == 4

    def test_reset_is_true(self):
        _, kwargs = self._call_get_pool()
        assert kwargs["reset"] is True

    def test_default_pool_size_is_5(self):
        """DB_POOL_SIZE 미설정 시 maxconnections=5."""
        mock_pool = MagicMock()
        client = _get_client()

        # DB_POOL_SIZE가 환경에 없도록 명시적으로 제거
        patched_env = {k: v for k, v in os.environ.items() if k != "DB_POOL_SIZE"}
        patched_env.update(_db_env())

        with patch.dict(os.environ, patched_env, clear=True):
            with patch("db.client.PooledDB", return_value=mock_pool) as mock_cls:
                client._get_pool()

        _, kwargs = mock_cls.call_args
        assert kwargs["maxconnections"] == 5

    def test_custom_pool_size(self):
        """DB_POOL_SIZE=10 설정 시 maxconnections=10."""
        _, kwargs = self._call_get_pool(extra_env={"DB_POOL_SIZE": "10"})
        assert kwargs["maxconnections"] == 10
        assert kwargs["maxcached"] == 10

    def test_empty_pool_size_falls_back_to_5(self):
        """DB_POOL_SIZE="" 빈 값이어도 int("") ValueError 없이 기본 5로 동작(#23 리뷰 P1-2)."""
        _, kwargs = self._call_get_pool(extra_env={"DB_POOL_SIZE": ""})
        assert kwargs["maxconnections"] == 5

    def test_empty_db_port_falls_back_to_3306(self):
        """DB_PORT="" 빈 값이어도 int("") ValueError 없이 기본 3306으로 동작(#23 리뷰 P1-2)."""
        _, kwargs = self._call_get_pool(extra_env={"DB_PORT": ""})
        assert kwargs["port"] == 3306

    def test_db_connect_kwargs_preserved(self):
        """기존 pymysql.connect 인자(charset, autocommit, init_command 등)가 유지돼야 한다."""
        _, kwargs = self._call_get_pool()

        assert kwargs["charset"] == "utf8mb4"
        assert kwargs["autocommit"] is False
        assert kwargs["init_command"] == "SET time_zone = '+09:00'"
        assert kwargs["host"] == "test-host"
        assert kwargs["user"] == "test-user"
        assert kwargs["database"] == "test-db"

    def test_missing_db_host_raises(self):
        """DB_HOST 미설정 시 RuntimeError가 발생해야 한다."""
        client = _get_client()
        env = _db_env()
        env.pop("DB_HOST")

        with patch.dict(os.environ, env, clear=True):
            with patch("db.client.PooledDB"):
                try:
                    client._get_pool()
                    assert False, "RuntimeError가 발생하지 않았다"
                except RuntimeError as e:
                    assert "DB_HOST" in str(e)


# --------------------------------------------------------------------------- #
# 테스트: _get_connection()
# --------------------------------------------------------------------------- #

class TestGetConnection:
    """_get_connection()이 풀에서 커넥션을 대여하는지 검증."""

    def test_calls_pool_connection(self):
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        client = _get_client()

        with patch.dict(os.environ, _db_env()):
            with patch("db.client.PooledDB", return_value=mock_pool):
                conn = client._get_connection()

        mock_pool.connection.assert_called_once()
        assert conn is mock_conn


# --------------------------------------------------------------------------- #
# 테스트: bounded-timeout / PoolExhaustedError (#71)
# --------------------------------------------------------------------------- #

class TestBoundedTimeout:
    """_get_connection() bounded 재시도 루프 및 PoolExhaustedError 검증 (#71)."""

    def test_raises_pool_exhausted_error_on_timeout(self):
        """풀 connection()이 항상 TooManyConnections를 던지면 timeout 후 PoolExhaustedError가 발생해야 한다."""
        from dbutils.pooled_db import TooManyConnections
        from db.client import PoolExhaustedError

        mock_pool = MagicMock()
        mock_pool.connection.side_effect = TooManyConnections()
        client = _get_client()

        with patch.dict(os.environ, _db_env()):
            with patch("db.client.PooledDB", return_value=mock_pool):
                # interval=0.0(실제 sleep 없음)·timeout=0.05s → 즉시 반복 재시도 후 에러
                with pytest.raises(PoolExhaustedError, match="커넥션 풀 소진"):
                    client._get_connection(timeout=0.05, interval=0.0)

        # 단발 호출이 아니라 재시도 루프가 실제로 반복됐는지 검증
        assert mock_pool.connection.call_count >= 2

    def test_succeeds_after_retry_on_too_many_connections(self):
        """처음 2번은 TooManyConnections, 3번째 시도에서 커넥션 반환 → 정상 반환해야 한다."""
        from dbutils.pooled_db import TooManyConnections
        from db.client import PoolExhaustedError

        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.side_effect = [
            TooManyConnections(),
            TooManyConnections(),
            mock_conn,  # 3번째 시도에서 성공
        ]
        client = _get_client()

        with patch.dict(os.environ, _db_env()):
            with patch("db.client.PooledDB", return_value=mock_pool):
                # interval을 0으로 줘서 sleep 없이 빠르게 재시도
                conn = client._get_connection(timeout=5.0, interval=0.0)

        assert conn is mock_conn, "재시도 성공 후 커넥션이 반환되어야 한다"
        assert mock_pool.connection.call_count == 3

    def test_first_success_does_not_sleep(self):
        """첫 시도에서 성공(sync 워커 정상 경로) 시 sleep이 호출되지 않아야 한다."""
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        client = _get_client()

        with patch.dict(os.environ, _db_env()):
            with patch("db.client.PooledDB", return_value=mock_pool):
                with patch("db.client.time") as mock_time:
                    mock_time.monotonic.return_value = 0.0
                    conn = client._get_connection(timeout=30.0)

        # sleep은 TooManyConnections 잡았을 때만 호출 — 첫 성공 시 호출 없어야 함
        mock_time.sleep.assert_not_called()
        assert conn is mock_conn

    def test_pool_exhausted_error_maps_to_503(self, client):
        """PoolExhaustedError 발생 시 Flask 핸들러가 503을 반환해야 한다 (#71)."""
        from db.client import PoolExhaustedError

        # errorhandler 직접 호출로 503 응답 확인
        with client.application.test_request_context():
            from app import handle_pool_exhausted
            response = handle_pool_exhausted(PoolExhaustedError("테스트"))
            # response는 (body, status_code) 튜플
            body, status = response
            assert status == 503
            assert "혼잡" in body
