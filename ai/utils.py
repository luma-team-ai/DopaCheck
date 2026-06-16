"""AI 모듈 공통 유틸리티."""
from __future__ import annotations

import re
from typing import Optional

import os

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
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = anthropic.Anthropic(api_key=api_key, timeout=AI_REQUEST_TIMEOUT)
    return _client


def extract_text(response) -> str:
    """응답 content에서 text 블록을 추출한다. tool_use만 반환 시 ValueError."""
    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        raise ValueError("응답에 text 블록이 없습니다 (tool_use only)")
    return text_block.text


def extract_json(text: str) -> str:
    """LLM 응답에서 JSON 부분만 추출 (마크다운 코드블록 제거)."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    # 코드블록 없이 JSON이 반환된 경우 { } 또는 [ ] 블록 추출
    m2 = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    return m2.group(1).strip() if m2 else text
