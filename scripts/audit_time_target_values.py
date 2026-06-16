"""[1회성] AI 생성 time 챌린지의 target_value 단위 오염 점검·교정 (#161 P2 후속).

배경:
    과거 ai/challenge.py 의 보정 로직이 임계값 100 이하 값을 시간으로 오판해 ×60 하던
    버그로, AI가 분 단위로 정상 반환한 목표(예: 60·90·300분)가 60배(3600·5400·…)로
    부풀려진 채 ai-join 으로 challenges 테이블에 저장됐다. 부풀려진 목표는 비현실적으로
    느슨해(주 수십 시간 한도) 달성 판정(time_total_min < target_value)이 사실상 항상
    통과된다. PR #207 이 생성 로직은 고쳤으나, 이미 저장된 과거 행은 잔존한다.

검출 한계(중요):
    오염값은 original×60 (original∈[1,99]) 이므로 60의 배수이고, 정상 분 목표(60·300·600…)
    역시 60의 배수일 수 있어 구조적으로 완전 구분이 불가능하다. 따라서 "비현실적으로 큰
    값"만 고신뢰 오염으로 본다. seed 의 정상 최댓값이 600분(주 10시간)이므로,
    주 20시간(1200분)을 초과하는 time 목표는 사람이 설정할 리 없는 오염으로 판단한다.

사용:
    점검(읽기 전용, 기본):   python -m scripts.audit_time_target_values
    교정(고신뢰 행만 /60):   python -m scripts.audit_time_target_values --fix

    --fix 는 target_value > 1200(주 20시간) 이고 60의 배수인 행만 ÷60 복원한다.
    [60, 1200] 구간의 모호한 행은 자동 교정하지 않고 목록만 출력하니 수동 확인할 것.

주의:
    교정으로 목표가 엄격해지면, 과거 느슨한 목표로 '달성(is_completed=1)' 처리된 참여
    행의 판정이 더 이상 맞지 않을 수 있다. --fix 후 영향 참여자에 대해 점수·완료 상태를
    재계산(services.score_service.recalculate_score)할지 별도 검토가 필요하다(이 스크립트는
    challenges.target_value 만 교정하고 user_challenges 는 건드리지 않는다).
"""
import argparse
import logging

from db.client import db

logger = logging.getLogger(__name__)

# 사람이 설정할 수 있는 time 목표의 현실적 상한(분). seed 최댓값 600(주 10시간)의 2배.
# 이 값을 초과하면 고신뢰 오염으로 간주한다.
SUSPECT_THRESHOLD_MIN = 1200


def audit(fix: bool = False) -> dict:
    """AI 생성 time 챌린지의 target_value 를 점검하고, fix=True 면 고신뢰 오염을 교정한다.

    Returns:
        {"total", "suspect", "ambiguous", "fixed"} 카운트 dict.
    """
    with db() as cursor:
        cursor.execute(
            "SELECT c.id, c.title, c.target_value, COUNT(uc.id) AS participants"
            " FROM challenges c"
            " LEFT JOIN user_challenges uc ON uc.challenge_id = c.id"
            " WHERE c.is_ai_generated = 1 AND c.target_type = 'time'"
            " GROUP BY c.id, c.title, c.target_value"
            " ORDER BY c.target_value DESC",
            (),
        )
        rows = cursor.fetchall() or []

        suspect, ambiguous, fixed = [], [], 0
        for r in rows:
            tv = int(r["target_value"])
            if tv > SUSPECT_THRESHOLD_MIN and tv % 60 == 0:
                suspect.append(r)
            elif tv % 60 == 0 and tv >= 60:
                # 60의 배수지만 현실 범위 [60,1200] — 오염/정상 구분 불가
                ambiguous.append(r)

        print(f"AI 생성 time 챌린지: 총 {len(rows)}건")
        print(f"  - 고신뢰 오염(>{SUSPECT_THRESHOLD_MIN}분, 60배수): {len(suspect)}건")
        print(f"  - 모호(60배수, {60}~{SUSPECT_THRESHOLD_MIN}분, 수동확인): {len(ambiguous)}건")

        if suspect:
            print("\n[고신뢰 오염 — 권장 교정값 = 현재÷60]")
            for r in suspect:
                print(
                    f"  id={r['id']}  '{r['title']}'  "
                    f"{r['target_value']}분 → {r['target_value'] // 60}분  "
                    f"(참여 {r['participants']}명)"
                )

        if ambiguous:
            print(f"\n[모호 — 자동교정 안 함, 수동 확인]")
            for r in ambiguous:
                print(
                    f"  id={r['id']}  '{r['title']}'  "
                    f"{r['target_value']}분  (참여 {r['participants']}명)"
                )

        if fix and suspect:
            for r in suspect:
                new_tv = int(r["target_value"]) // 60
                cursor.execute(
                    "UPDATE challenges SET target_value = %s"
                    " WHERE id = %s AND is_ai_generated = 1 AND target_type = 'time'"
                    " AND target_value = %s",
                    (new_tv, r["id"], r["target_value"]),
                )
                fixed += cursor.rowcount
                logger.info(
                    "교정 id=%s '%s': %s → %s분",
                    r["id"], r["title"], r["target_value"], new_tv,
                )
            print(f"\n교정 완료: {fixed}건 (target_value ÷60)")
            print(
                "  ⚠️ 참여자 완료/점수 상태는 미조정 — 필요 시 영향 user_id 에 대해"
                " recalculate_score 재실행 검토."
            )
        elif fix:
            print("\n교정 대상(고신뢰 오염) 없음.")

    return {
        "total": len(rows),
        "suspect": len(suspect),
        "ambiguous": len(ambiguous),
        "fixed": fixed,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="AI time 챌린지 target_value 단위 오염 점검")
    parser.add_argument(
        "--fix", action="store_true",
        help=f"고신뢰 오염(>{SUSPECT_THRESHOLD_MIN}분, 60배수)만 ÷60 교정한다(기본: 점검만)",
    )
    args = parser.parse_args()
    audit(fix=args.fix)
