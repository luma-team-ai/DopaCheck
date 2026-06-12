"""시간 소비 분석 (담당: 이은석 — FR-9~15)."""
from flask import Blueprint, render_template, request

from routes.auth import login_required

time_bp = Blueprint("time", __name__, url_prefix="/time")


@time_bp.route("")
@login_required
def time_page():
    """앱별 주간 사용 시간 + 시급 입력 폼. (FR-9, FR-10)"""
    return render_template("time/index.html")


@time_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """시간 분석 파이프라인.

    1. 유튜브·인스타·틱톡·게임 시간(h) + 시급(원) 입력 검증 (FR-9, FR-10)
    2. SNS 시간 환산: 책 N권 / 강의 N개 / 운동 N회 (FR-11 — config.py 상수)
    3. 게임 시간 환산: 시급 기준 N원짜리 취미 (FR-12)
    4. ai.comment.generate("time", context) 호출 (FR-14)
    5. 도넛 차트 데이터 구성 → 템플릿 렌더 (FR-13)
    6. time_records 저장 + 도파민 점수 재산출 트리거 (FR-15, FR-31)
    """
    # TODO(이은석): 위 파이프라인 구현 — AI 호출은 try/except로 감싸 fallback 제공 (FR-45)
    raise NotImplementedError
