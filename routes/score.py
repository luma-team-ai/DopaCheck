"""도파민 점수 + 랭킹 (담당: 김승현 — FR-26~31)."""
from flask import Blueprint, render_template

from routes.auth import login_required

score_bp = Blueprint("score", __name__, url_prefix="/score")


@score_bp.route("")
@login_required
def score_page():
    """도파민 점수 페이지.

    1. dopamine_scores에서 이번 주 점수 조회 (FR-26)
    2. 항목별 기여도 시각화 데이터 (FR-28)
    3. 전체 사용자 평균 대비 내 점수 (FR-29)
    4. 상위 N% 랭킹 — 시드 더미 데이터 20건 전제 (FR-30)
    """
    # TODO(김승현): 위 페이지 구현
    return render_template("score/index.html")


def recalculate_score(user_id: str) -> None:
    """분석 결과 저장 시 호출되는 점수 재산출 공통 함수. (FR-31)

    delivery/time/challenge 라우트에서 저장 직후 호출한다.
    1. 이번 주 배달·시간·챌린지 데이터 집계
    2. ai.score.calculate(data) 호출
    3. dopamine_scores (user_id, week_start) upsert
    4. 챌린지 달성 판정 트리거 (FR-37) → 달성 시 +5점 보너스 (FR-38)
    """
    # TODO(김승현): 구현 — 챌린지 달성 판정 연동은 오영석과 협의
    raise NotImplementedError
