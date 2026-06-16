"""[1회성] 도파민 점수 모델 반전(#175) 후 과거 dopamine_scores 재계산 백필.

운영 배포 직후 1회 실행: python -m scripts.backfill_scores
"""
import logging
from services.score_service import backfill_all_scores

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updated = backfill_all_scores()
    print(f"백필 완료: {updated}개 행 재계산")
