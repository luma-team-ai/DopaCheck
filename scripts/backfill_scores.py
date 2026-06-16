"""[1회성] 도파민 점수 모델 반전(#175) 후 과거 dopamine_scores 재계산 백필.

운영 배포 직후 1회 실행: python -m scripts.backfill_scores

주의:
- 전체 행을 한 트랜잭션에서 갱신하므로 트래픽이 낮은 시간대에 실행한다(실행 중 점수 저장 대기 가능).
- 실행 후 db/migrations/004_add_challenge_bonus_check.sql 을 적용한다(백필로 양수 보너스가
  음수 감점으로 교정된 뒤라야 CHECK 제약 추가가 성공한다).
"""
import logging
from services.score_service import backfill_all_scores

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updated = backfill_all_scores()
    print(f"백필 완료: {updated}개 행 재계산")
