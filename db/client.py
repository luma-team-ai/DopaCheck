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
    - 재로그인: 닉네임 갱신 후 id 반환
    반환값: user_id (BIGINT)
    """
    with db() as cursor:
        # 이미 존재하면 닉네임 갱신 후 id 반환 (P2: 재로그인 시 닉네임 미갱신 수정)
        cursor.execute(
            "SELECT id FROM users WHERE provider = %s AND provider_id = %s",
            (provider, provider_id)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE users SET nickname = %s WHERE id = %s",
                (nickname, row["id"])
            )
            return row["id"]

        # 없으면 INSERT — ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)로
        # 항상 올바른 id를 반환 (P2: LAST_INSERT_ID()=0 버그 방지)
        cursor.execute(
            """
            INSERT INTO users (email, nickname, provider, provider_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id), nickname=VALUES(nickname)
            """,
            (email, nickname, provider, provider_id)
        )
        new_id = cursor.lastrowid
        if new_id:
            return new_id

        # fallback: LAST_INSERT_ID가 0인 경우 SELECT로 재조회
        cursor.execute(
            "SELECT id FROM users WHERE provider = %s AND provider_id = %s",
            (provider, provider_id)
        )
        return cursor.fetchone()["id"]