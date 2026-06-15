"""MariaDB 커넥션 팩토리 (#21 — Supabase에서 전환, #23 — 커넥션 풀 도입, #71 — bounded timeout).

DB 접근은 반드시 이 모듈의 db() 컨텍스트매니저를 통해서만 한다.
(라우트마다 pymysql.connect 직접 호출 금지 — 키 관리·트랜잭션 단일화)

사용 예:
    from db.client import db

    with db() as cursor:
        cursor.execute(
            "SELECT id, total_price FROM delivery_records WHERE user_id = %s",
            (user_id,),
        )
        rows = cursor.fetchall()   # autocommit=False → with 정상 종료 시 commit

RLS는 제거됐다 — 모든 조회는 앱에서 WHERE user_id = %s 로 스코프할 것.

커넥션 풀 (#23):
    - DBUtils.PooledDB를 사용해 요청마다 pymysql.connect() 신규 생성하는 비용을 제거.
    - 풀은 모듈 수준 싱글톤으로 지연 초기화된다(import 시 DB 접속 없음).
    - 환경변수 DB_POOL_SIZE(미설정 시 기본 5)로 최대 커넥션 수를 제어한다.
    - Gunicorn 멀티워커 환경에서 풀은 워커 프로세스별로 독립 생성된다.

bounded-timeout (#71):
    - blocking=False 로 변경 → 풀 소진 시 TooManyConnections 즉시 발생(무한 대기 제거).
    - _get_connection()에서 DB_POOL_TIMEOUT(기본 30초) 내 재시도 루프를 수행한다.
    - 타임아웃 초과 시 PoolExhaustedError(RuntimeError) 발생 → app.py에서 503으로 매핑.
    - sync 워커에선 풀이 소진되지 않으므로 첫 시도에서 항상 성공(동작 동일).

pool-timeout 캐싱 (#93):
    - DB_POOL_TIMEOUT 환경변수를 요청마다 재평가하지 않고 최초 1회만 읽어 캐싱한다.
    - DB_POOL_SIZE가 _build_pool()에서 1회 고정되는 것과 일관된 정책.
    - import 시 즉시 읽지 않고(lazy) _resolve_pool_timeout() 최초 호출 시 확정된다.
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager

import pymysql
from dbutils.pooled_db import PooledDB, TooManyConnections
from pymysql.cursors import DictCursor


class PoolExhaustedError(RuntimeError):
    """커넥션 풀 소진 시 bounded timeout 초과 → 503 매핑용 예외 (#71)."""


# 풀 소진 시 재시도 폴링 간격 (초). monkeypatch로 교체 가능하도록 모듈 상수로 분리.
_POOL_RETRY_INTERVAL = 0.05  # 50ms


def _env(key: str) -> str:
    """필수 환경변수를 읽는다. 누락 시 명확한 메시지로 실패시킨다."""
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"환경변수 {key} 가 설정되지 않았습니다. .env.example 참고 후 .env에 설정하세요."
        )
    return value


# --------------------------------------------------------------------------- #
# 풀 싱글톤 — 지연 초기화 (import 시 DB 접속 금지)
# --------------------------------------------------------------------------- #
_pool: PooledDB | None = None
_pool_lock = threading.Lock()

# --------------------------------------------------------------------------- #
# 타임아웃 캐시 — 지연 1회 읽기 (#93)
# --------------------------------------------------------------------------- #
# _pool_timeout: None이면 아직 미결정. _resolve_pool_timeout() 최초 호출 시 확정.
# 테스트 간 오염 방지를 위해 reset_pool 픽스처에서 None으로 리셋한다.
_pool_timeout: float | None = None


def _resolve_pool_timeout() -> float:
    """DB_POOL_TIMEOUT(초)을 1회만 읽어 캐싱한다. 미설정 시 기본 30. (#93)

    import 시 즉시 읽지 않고(lazy) 최초 호출 시 값을 확정한다.
    이후 호출은 캐시된 값을 그대로 반환 — env 재평가 없음.
    빈 문자열("") 방어: `or "30"` 으로 int("") ValueError 를 방지한다.
    """
    global _pool_timeout
    if _pool_timeout is None:
        _pool_timeout = float(os.environ.get("DB_POOL_TIMEOUT") or "30")
    return _pool_timeout


def _get_pool() -> PooledDB:
    """모듈 수준 커넥션 풀을 반환한다. 최초 호출 시 생성(지연 초기화).

    스레드 안전성: PooledDB 생성 시 mincached 커넥션 소켓 I/O로 GIL이 릴리스되므로,
    double-checked locking으로 gthread/eventlet 워커에서도 풀 중복 생성을 차단한다.
    멀티프로세스(Gunicorn): 프로세스마다 별도 풀 생성 — 의도된 동작.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = _build_pool()
    return _pool


def _build_pool() -> PooledDB:
    # DB_POOL_SIZE/DB_PORT가 빈 문자열("")로 설정돼도 int("")=ValueError를 내지 않도록
    # `or` 기본값 사용(환경변수 존재+빈값 케이스 방어).
    pool_size = int(os.environ.get("DB_POOL_SIZE") or "5")
    return PooledDB(
            creator=pymysql,
            maxconnections=pool_size,
            mincached=1,
            maxcached=pool_size,
            # blocking=False: 풀 소진 시 무한 대기 대신 TooManyConnections 즉시 발생.
            # _get_connection()에서 DB_POOL_TIMEOUT(기본 30초) bounded 재시도 루프로 처리.
            # sync 워커에선 풀이 소진되지 않으므로 첫 시도에서 항상 성공(동작 동일) — #71.
            blocking=False,
            ping=4,          # 쿼리 실행 전 커넥션 유효성 확인(유휴 끊김 방지)
            reset=True,      # 반납 시 rollback 강제 — commit 완료 후엔 빈 트랜잭션이라 no-op
            # --- pymysql.connect 인자 ---
            host=_env("DB_HOST"),
            port=int(os.environ.get("DB_PORT") or "3306"),
            user=_env("DB_USER"),
            password=_env("DB_PASSWORD"),
            database=_env("DB_NAME"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
            # #11 KST 정책: 세션 타임존을 +09:00으로 고정한다.
            # CURRENT_TIMESTAMP(created_at 기본값)와 경계 비교를 모두 KST-naive로 일원화 —
            # 서버 컨테이너 TZ(UTC 등)와 무관하게 주차 경계가 KST 기준으로 동작한다.
            init_command="SET time_zone = '+09:00'",
        )


def _get_connection(timeout: float | None = None, interval: float = _POOL_RETRY_INTERVAL):
    """풀에서 커넥션을 대여한다(db() 내부 구현 세부 — 외부 직접 호출 금지).

    반환된 커넥션은 사용 후 .close()를 호출해야 풀에 반납된다. close 누락 시
    풀 커넥션이 영구 점유돼 누수되므로, 호출자는 항상 db() 컨텍스트매니저를 사용할 것.

    풀 소진(TooManyConnections) 시 bounded 재시도 루프를 수행한다 (#71):
    - timeout: 최대 대기 시간(초). None 이면 _resolve_pool_timeout()(#93 캐싱) 값 사용.
      timeout= 인자를 명시하면 캐시를 무시하고 그 값으로 동작(테스트 주입 경로 유지).
    - interval: 재시도 폴링 간격(초). 기본 _POOL_RETRY_INTERVAL(50ms).
    - timeout 초과 시 PoolExhaustedError 발생.
    - sync 워커에선 첫 시도에서 항상 성공 → sleep/timeout 경로를 타지 않음.
    """
    if timeout is None:
        timeout = _resolve_pool_timeout()  # 1회 캐싱 (#93); env 매 호출 재평가 제거

    deadline = time.monotonic() + timeout
    while True:
        try:
            return _get_pool().connection()
        except TooManyConnections:
            if time.monotonic() >= deadline:
                raise PoolExhaustedError(
                    f"커넥션 풀 소진: {timeout:.0f}초 내 커넥션 확보 실패"
                )
            time.sleep(interval)


@contextmanager
def db():
    """커넥션·커서 컨텍스트매니저.

    - 정상 종료: commit
    - 예외 발생: rollback 후 재raise
    - 항상 커넥션 close (풀에 반납)

    외부에서 보는 계약은 기존과 동일하다:
        with db() as cursor:
            cursor.execute(...)
    """
    conn = _get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_user_profile(email: str, nickname: str, provider: str, provider_id: str) -> int:
    """소셜 로그인 시 users 테이블에 프로필 upsert.

    - 최초 로그인: INSERT → lastrowid 반환
    - 재로그인: ON DUPLICATE KEY UPDATE로 닉네임 갱신 + LAST_INSERT_ID(id)로 기존 id 반환
    - P2 수정: SELECT→INSERT 비원자적 분기(TOCTOU) 제거 → 단일 쿼리로 경쟁 조건 원천 차단
    반환값: user_id (BIGINT)
    """
    with db() as cursor:
        # INSERT … ON DUPLICATE KEY UPDATE 단일 쿼리:
        # - 신규: INSERT 성공 → lastrowid = 새 id
        # - 중복: LAST_INSERT_ID(id) 트릭으로 기존 id를 lastrowid에 노출 + nickname 갱신
        # provider+provider_id 쌍에 UNIQUE 제약이 있어야 ON DUPLICATE가 작동한다.
        cursor.execute(
            """
            INSERT INTO users (email, nickname, provider, provider_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id       = LAST_INSERT_ID(id),
                nickname = VALUES(nickname)
            """,
            (email, nickname, provider, provider_id)
        )
        user_id = cursor.lastrowid
        if user_id:
            return user_id

        # lastrowid가 0인 극히 드문 드라이버 엣지케이스 — SELECT fallback
        cursor.execute(
            "SELECT id FROM users WHERE provider = %s AND provider_id = %s",
            (provider, provider_id)
        )
        return cursor.fetchone()["id"]
