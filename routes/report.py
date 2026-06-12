"""종합 리포트 + SNS 공유 카드 (담당: 정재봉 — FR-16~20)."""
from flask import Blueprint, render_template

from routes.auth import login_required

report_bp = Blueprint("report", __name__, url_prefix="/report")


@report_bp.route("")
@login_required
def report_page():
    """배달 지출·시간 소비 통합 대시보드.

    1. delivery_records + time_records 주간 집계 조회 (FR-16)
    2. 도파민 점수 표시 (FR-18)
    3. ai.comment.generate("report", context) — 종합 인사이트 (FR-17)
    4. 저번 주 vs 이번 주 비교 차트 데이터 (FR-20)
    5. 공유 카드 영역 → html2canvas로 이미지 저장/SNS 공유 (FR-19, 클라이언트 측)
    """
    # TODO(정재봉): 위 대시보드 구현
    return render_template("report/index.html")
