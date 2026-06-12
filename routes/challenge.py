"""AI 챌린지 (담당: 오영석 — FR-32~38)."""
from flask import Blueprint, render_template, request

from routes.auth import login_required

challenge_bp = Blueprint("challenge", __name__, url_prefix="/challenge")


@challenge_bp.route("")
@login_required
def challenge_page():
    """챌린지 목록 페이지.

    1. 기본 챌린지 목록 조회 (FR-32)
    2. 히스토리 1건 이상이면 ai.challenge.recommend(history) 호출 (FR-33)
    3. 참여 중 챌린지 달성률 프로그레스 바 (FR-36)
    """
    # TODO(오영석): 위 페이지 구현
    return render_template("challenge/index.html")


@challenge_bp.route("/<challenge_id>/join", methods=["POST"])
@login_required
def join(challenge_id: str):
    """챌린지 참여 + 목표 설정. (FR-34)

    동일 챌린지 활성 상태 중복 참여 차단 (FR-35 — DB unique index와 이중 방어)
    """
    # TODO(오영석): user_challenges insert → 중복 시 에러 메시지
    raise NotImplementedError
