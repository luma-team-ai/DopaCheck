"""AI 모듈 공통 유틸리티."""
from __future__ import annotations

import re
from typing import Optional

import anthropic

from config import AI_REQUEST_TIMEOUT

# ── 단일 클라이언트 팩토리 ────────────────────────────────
# 모든 ai/* 모듈이 이 함수를 통해 클라이언트를 얻는다.
# - timeout: 응답 지연 시 무한 대기 방지 (AI_REQUEST_TIMEOUT 초)
# - 모듈 레벨에서 한 번만 생성해 재사용한다.
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    """타임아웃이 설정된 Anthropic 클라이언트를 반환한다. (싱글턴)"""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=AI_REQUEST_TIMEOUT)
    return _client


def extract_json(text: str) -> str:
    """LLM 응답에서 JSON 부분만 추출 (마크다운 코드블록 제거)."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return m.group(1).strip() if m else text
