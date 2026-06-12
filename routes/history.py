"""분석 히스토리 (담당: 허남 — FR-21~25)."""
from flask import Blueprint, render_template, request

from routes.auth import login_required

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("")
@login_required
def history_list():
    """날짜별 분석 기록 목록. (FR-21)

    쿼리 파라미터 ?period=week|month|all 필터 지원 (FR-24)
    같은 날 동일 유형 분석은 누적 표시 — 덮어쓰기 없음 (FR-25)
    """
    # TODO(허남): delivery_records + time_records 통합 목록 조회
    return render_template("history/index.html")


@history_bp.route("/<record_id>")
@login_required
def history_detail(record_id: str):
    """특정 기록 상세 조회. (FR-22)"""
    # TODO(허남): 기록 유형(delivery/time) 구분 조회 — URL 설계는 자유 (예: ?type=delivery)
    return render_template("history/detail.html")


@history_bp.route("/<record_id>", methods=["DELETE"])
@login_required
def history_delete(record_id: str):
    """기록 삭제. (FR-23)

    삭제 후 도파민 점수 재산출 여부는 팀 합의 필요.
    """
    # TODO(허남): 본인 기록인지 확인 후 삭제 → 204 또는 JSON 응답
    raise NotImplementedError
