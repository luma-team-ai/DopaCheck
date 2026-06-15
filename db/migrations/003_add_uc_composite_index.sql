-- 마이그레이션: user_challenges 복합 인덱스 추가 (#113 TOCTOU 후속, #120/#123)
--
-- 현상: 챌린지 join 시 SELECT … FOR UPDATE의 next-key lock이 올바른 범위에 걸리려면
--       WHERE 절(user_id = ? AND challenge_id = ? AND is_completed = 0)을 커버하는
--       (user_id, challenge_id) 복합 인덱스가 필요하다.
-- 원인: PR #120이 db/schema.sql 에만 인덱스를 추가 — 신규 설치(CREATE TABLE IF NOT EXISTS)
--       에만 반영되고, 운영 DB의 기존 user_challenges 테이블에는 인덱스가 생기지 않았다.
--       인덱스 없이 풀 스캔 시 gap lock 범위가 의도와 달라져 TOCTOU가 잔존할 수 있다.
--
-- 대상: 운영 DB(Cloudtype MariaDB)의 기존 user_challenges 테이블.
-- db/schema.sql 은 신규 설치에만 적용되므로, 기존 테이블에는 이 ALTER 문을 별도로 실행해야 한다.
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 아래 문을 그대로 실행.
--       MariaDB 10.0.2+ 의 IF NOT EXISTS 로 재실행해도 안전(이미 있으면 무시).

ALTER TABLE user_challenges
  ADD INDEX IF NOT EXISTS idx_uc_user_challenge (user_id, challenge_id);

-- 적용 확인: SHOW INDEX FROM user_challenges; 에 idx_uc_user_challenge 가 보이면 정상.
