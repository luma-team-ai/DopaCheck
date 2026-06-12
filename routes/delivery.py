"""배달 영수증 분석 (담당: 김관영 — FR-1~8)."""
from flask import Blueprint, render_template, request

from routes.auth import login_required

delivery_bp = Blueprint("delivery", __name__, url_prefix="/delivery")


@delivery_bp.route("")
@login_required
def delivery_page():
    """영수증 업로드 폼. (FR-1)"""
    return render_template("delivery/index.html")


@delivery_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """영수증 분석 파이프라인.

    1. 업로드 이미지 검증 (JPG/PNG — FR-1)
    2. ai.ocr.parse_receipt() 호출 → 실패 시 수동 입력 폼 fallback (FR-2, FR-7)
    3. 사용자 확인/수정 값 기준 ai.calorie.estimate() 호출 (FR-3)
    4. 지출 환산(치킨 N마리/헬스장 N개월 — FR-4), 칼로리 환산(러닝 N분/걷기 N시간 — FR-5)
       → config.py 상수 사용
    5. ai.comment.generate("delivery", context) 호출 (FR-6)
    6. delivery_records 저장 + 도파민 점수 재산출 트리거 (FR-8, FR-31)
    """
    # TODO(김관영): 위 파이프라인 구현 — AI 호출은 try/except로 감싸 fallback 제공 (FR-45)
    raise NotImplementedError
