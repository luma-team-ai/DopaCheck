-- 마이그레이션: dopamine_scores.challenge_bonus CHECK 제약 추가 (#175 점수 모델 반전)
--
-- 현상: 점수 의미 반전(#175)으로 challenge_bonus 가 챌린지 달성 "감점"(0~-20 음수)을
--       저장하는 컬럼이 됐다. score 컬럼엔 CHECK (0~100)가 있으나 challenge_bonus 엔 없어
--       부호 버그가 생겨도 DB가 막지 못한다.
-- 원인: db/schema.sql 의 CHECK 는 CREATE TABLE IF NOT EXISTS 에만 적용 — 신규 설치에만
--       반영되고 운영 DB의 기존 dopamine_scores 테이블에는 제약이 생기지 않는다.
--
-- 대상: 운영 DB(Cloudtype MariaDB)의 기존 dopamine_scores 테이블.
--
-- ⚠️ 실행 순서(중요): 반드시 백필을 먼저 실행한 뒤 이 ALTER 를 실행한다.
--   1) python -m scripts.backfill_scores   ← 과거 행을 새 공식으로 재계산(양수 보너스→음수 감점)
--   2) 아래 ALTER 실행                       ← 모든 행이 -20~0 범위가 된 뒤라야 제약 추가가 성공
--   (순서를 바꾸면 기존 양수 challenge_bonus(예: +14) 행이 CHECK 를 위반해 ALTER 가 실패한다.)
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 아래 문을 실행.

ALTER TABLE dopamine_scores
  ADD CONSTRAINT chk_challenge_bonus CHECK (challenge_bonus BETWEEN -20 AND 0);

-- 적용 확인: SHOW CREATE TABLE dopamine_scores; 에 chk_challenge_bonus 가 보이면 정상.
