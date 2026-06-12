"""MariaDB 커넥션 팩토리 (#21 — Supabase에서 전환).

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
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


def _env(key: str) -> str:
    """필수 환경변수를 읽는다. 누락 시 명확한 메시지로 실패시킨다."""
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"환경변수 {key} 가 설정되지 않았습니다. .env.example 참고 후 .env에 설정하세요."
        )
    return value


def get_connection() -> pymysql.connections.Connection:
    """MariaDB 커넥션을 새로 생성한다.

    TODO(#21 후속): 커넥션 풀(DBUtils.PooledDB 등) 도입 — 현재는 요청당 신규 커넥션.
    """
    return pymysql.connect(
        host=_env("DB_HOST"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=_env("DB_USER"),
        password=_env("DB_PASSWORD"),
        db=_env("DB_NAME"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        # #11 KST 정책: 세션 타임존을 +09:00으로 고정한다.
        # CURRENT_TIMESTAMP(created_at 기본값)와 경계 비교를 모두 KST-naive로 일원화 —
        # 서버 컨테이너 TZ(UTC 등)와 무관하게 주차 경계가 KST 기준으로 동작한다.
        init_command="SET time_zone = '+09:00'",
    )


@contextmanager
def db():
    """커넥션·커서 컨텍스트매니저.

    - 정상 종료: commit
    - 예외 발생: rollback 후 재raise
    - 항상 커넥션 close
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
