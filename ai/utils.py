"""AI 모듈 공통 유틸리티."""
import re


def extract_json(text: str) -> str:
    """LLM 응답에서 JSON 부분만 추출 (마크다운 코드블록 제거)."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return m.group(1).strip() if m else text
