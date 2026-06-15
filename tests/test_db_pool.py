"""커넥션 풀 단위 테스트 (#23, #71, #93).

실제 네트워크 접속 없이 _get_pool() 싱글톤 동작과
PooledDB 생성 인자를 검증한다.

#71 추가: bounded-timeout / PoolExhaustedError 동작 검증.
#93 추가: DB_POOL_TIMEOUT lazy 1회 캐싱(_resolve_pool_timeout) 동작 검증.
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
    """각 테스트 전후에 db.client._pool 및 _pool_timeout을 None으로 초기화한다.

    _pool이 mock 객체로 남으면 이후 테스트(report 등)가 실제 DB 대신
    MagicMock에서 커넥션을 받아 TypeError를 일으키므로 반드시 정리해야 한다.
    _pool_timeout 캐시(#93)도 함께 리셋해 env patch 테스트가 서로 오염되지 않도록 한다.
    """
    import db.client as client_mod
    client_mod._pool = None
    client_mod._pool_timeout = None
    yield
    client_mod._pool = None
    client_mod._pool_timeout = None


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


# --------------------------------------------------------------------------- #
# 테스트: _resolve_pool_timeout() 캐싱 동작 (#93)
# --------------------------------------------------------------------------- #

class TestResolvePoolTimeout:
    """_resolve_pool_timeout()이 env를 1회만 읽어 캐싱하는지 검증 (#93)."""

    def test_default_is_30_when_env_not_set(self):
        """DB_POOL_TIMEOUT 미설정 시 기본값 30.0을 반환해야 한다."""
        client = _get_client()

        # DB_POOL_TIMEOUT이 환경에 없도록 명시적으로 제거 후 확인
        env_without_timeout = {k: v for k, v in os.environ.items() if k != "DB_POOL_TIMEOUT"}
        with patch.dict(os.environ, env_without_timeout, clear=True):
            result = client._resolve_pool_timeout()

        assert result == 30.0

    def test_reads_env_value_when_set(self):
        """DB_POOL_TIMEOUT=60 설정 시 60.0을 반환해야 한다."""
        client = _get_client()

        with patch.dict(os.environ, {"DB_POOL_TIMEOUT": "60"}, clear=False):
            result = client._resolve_pool_timeout()

        assert result == 60.0

    def test_empty_env_falls_back_to_30(self):
        """DB_POOL_TIMEOUT="" 빈 값이어도 기본 30.0으로 동작해야 한다."""
        client = _get_client()

        with patch.dict(os.environ, {"DB_POOL_TIMEOUT": ""}, clear=False):
            result = client._resolve_pool_timeout()

        assert result == 30.0

    def test_caches_value_on_first_call(self):
        """두 번 호출해도 env를 1회만 읽어 첫 번째 값으로 고정돼야 한다 (#93).

        첫 호출에서 DB_POOL_TIMEOUT=45로 캐싱한 뒤,
        env를 20으로 바꿔도 두 번째 호출은 여전히 45를 반환해야 한다.
        """
        client = _get_client()

        # 첫 호출: 45로 캐싱
        with patch.dict(os.environ, {"DB_POOL_TIMEOUT": "45"}, clear=False):
            first = client._resolve_pool_timeout()

        assert first == 45.0
        # 캐시가 살아있는 상태에서 env를 변경해도 캐시 값이 유지돼야 함
        with patch.dict(os.environ, {"DB_POOL_TIMEOUT": "20"}, clear=False):
            second = client._resolve_pool_timeout()

        assert second == 45.0, "캐싱 후 env 변경이 두 번째 호출 결과에 영향을 주면 안 된다"

    def test_cache_is_none_before_first_call(self):
        """_pool_timeout 캐시 변수가 None으로 시작해야 한다(import-time 즉시 읽기 금지)."""
        client = _get_client()
        assert client._pool_timeout is None

    def test_concurrent_resolve_initializes_once(self):
        """두 스레드가 동시 진입해도 DCL로 1회만 초기화·동일 값 반환해야 한다 (#102).

        threading.Barrier로 두 스레드를 동시에 _resolve_pool_timeout()에 진입시켜,
        이중검증 락(double-checked locking)이 중복 초기화를 막는지 검증한다.
        """
        import threading

        client = _get_client()
        results = []
        barrier = threading.Barrier(2)

        def call():
            barrier.wait()  # 두 스레드를 동시에 출발시킴
            results.append(client._resolve_pool_timeout())

        with patch.dict(os.environ, {"DB_POOL_TIMEOUT": "45"}, clear=False):
            threads = [threading.Thread(target=call) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert results == [45.0, 45.0]
        assert client._pool_timeout == 45.0  # 한 번만 확정됨

    def test_get_connection_uses_cached_timeout_when_no_arg(self):
        """timeout= 인자 없이 _get_connection() 호출 시 _resolve_pool_timeout() 캐시값을 사용해야 한다."""
        from dbutils.pooled_db import TooManyConnections
        from db.client import PoolExhaustedError

        mock_pool = MagicMock()
        mock_pool.connection.side_effect = TooManyConnections()
        client = _get_client()

        # 1) DB_POOL_TIMEOUT=1 로 먼저 캐싱
        with patch.dict(os.environ, {**_db_env(), "DB_POOL_TIMEOUT": "1"}, clear=False):
            assert client._resolve_pool_timeout() == 1.0

        # 2) env를 999로 바꿔도 _get_connection()은 캐시값(1초)을 사용해야 한다
        #    (매 호출 env 재평가가 아님을 증명 — 999가 아닌 1초로 타임아웃)
        with patch.dict(os.environ, {**_db_env(), "DB_POOL_TIMEOUT": "999"}, clear=False):
            with patch("db.client.PooledDB", return_value=mock_pool):
                with pytest.raises(PoolExhaustedError, match="1초"):
                    client._get_connection(interval=0.0)  # timeout 인자 없음 → 캐시값
