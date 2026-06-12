"""Supabase 클라이언트 팩토리 (담당: 김승현).

DB 접근은 반드시 이 모듈의 get_supabase()를 통해서만 한다.
(라우트마다 create_client 직접 호출 금지 — 키 관리 단일화)
"""
from __future__ import annotations

import os

from supabase import Client, create_client

_client: Client | None = None


def get_supabase() -> Client:
    """anon key 기반 Supabase 클라이언트 싱글톤을 반환한다."""
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client


# TODO(김승현): RLS 적용 시 사용자 토큰 기반 클라이언트 발급 함수 추가 검토
#   def get_supabase_for_user(access_token: str) -> Client: ...
