-- 마이그레이션: challenges 중복 데이터 정리 + title UNIQUE 제약 추가 (#97)
--
-- 현상: 기본 챌린지 7종이 14건으로 중복 (id 1~7과 8~14가 완전히 동일한 행).
-- 원인: 시드 스크립트가 UPSERT 없이 2회 실행됨.
--
-- 대상: 운영 DB(Cloudtype MariaDB)의 기존 challenges 테이블.
-- db/schema.sql 은 신규 설치(CREATE TABLE IF NOT EXISTS)에만 적용되므로,
-- 기존 테이블에는 이 스크립트를 별도로 실행해야 한다.
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 아래 문을 그대로 실행.

-- 1) 중복 행 제거: title별로 가장 작은 id만 남기고 나머지 삭제.
--    (user_challenges.challenge_id가 삭제 대상을 참조하는 경우 남길 id로 먼저 재매핑)
UPDATE user_challenges uc
JOIN challenges dup ON uc.challenge_id = dup.id
JOIN (
  SELECT title, MIN(id) AS keep_id
  FROM challenges
  GROUP BY title
) keep ON keep.title = dup.title
SET uc.challenge_id = keep.keep_id
WHERE dup.id <> keep.keep_id;

DELETE c FROM challenges c
JOIN (
  SELECT title, MIN(id) AS keep_id
  FROM challenges
  GROUP BY title
) keep ON keep.title = c.title
WHERE c.id <> keep.keep_id;

-- 2) 재발 방지: title UNIQUE 제약 추가 (재시드 시 ON DUPLICATE KEY UPDATE로 안전하게 처리되도록)
ALTER TABLE challenges
  ADD UNIQUE KEY uq_challenges_title (title);
