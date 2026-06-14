"""MariaDB 커넥션 팩토리 (#21 — Supabase에서 전환, #23 — 커넥션 풀 도입).

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
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager

import pymysql
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor


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
            # 풀 소진 시 에러 대신 대기. 현재 배포는 gunicorn sync 워커(워커당 동시 1요청,
            # maxconnections≫1)라 소진/대기가 발생하지 않는다. gthread/eventlet 전환 시
            # 무한 대기 위험이 있어 bounded-timeout/503 처리는 후속 이슈로 분리(#23 리뷰 P1-1).
            blocking=True,
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


def _get_connection():
    """풀에서 커넥션을 대여한다(db() 내부 구현 세부 — 외부 직접 호출 금지).

    반환된 커넥션은 사용 후 .close()를 호출해야 풀에 반납된다. close 누락 시
    풀 커넥션이 영구 점유돼 누수되므로, 호출자는 항상 db() 컨텍스트매니저를 사용할 것.
    """
    return _get_pool().connection()


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
