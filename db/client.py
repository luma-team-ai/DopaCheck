# db/client.py
import pymysql
import os
from contextlib import contextmanager


def get_connection():
    """MariaDB 커넥션 반환"""
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        db=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


@contextmanager
def db():
    """
    커넥션 컨텍스트 매니저 — 자동 commit/rollback
    사용법:
        with db() as cursor:
            cursor.execute("SELECT ...")
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


def upsert_user_profile(email: str, nickname: str, provider: str, provider_id: str) -> int:
    """
    소셜 로그인 시 users 테이블에 프로필 생성/조회
    - 최초 로그인: INSERT
    - 재로그인: 기존 레코드 조회 후 반환
    반환값: user_id (BIGINT)
    """
    with db() as cursor:
        # 이미 존재하면 조회
        cursor.execute(
            "SELECT id FROM users WHERE provider = %s AND provider_id = %s",
            (provider, provider_id)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]

        # 없으면 INSERT
        cursor.execute(
            """
            INSERT INTO users (email, nickname, provider, provider_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE nickname = VALUES(nickname)
            """,
            (email, nickname, provider, provider_id)
        )
        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        return cursor.fetchone()["id"]