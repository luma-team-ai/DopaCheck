-- 마이그레이션: users 테이블에 role 컬럼 추가 (PRD Ver1.2 — 관리자 페이지 FR-52~54)
--
-- 대상: 운영 DB(Cloudtype MariaDB)의 기존 users 테이블 (이미 데이터 존재).
-- db/schema.sql 은 신규 설치(CREATE TABLE IF NOT EXISTS)에만 적용되므로,
-- 기존 테이블에는 이 ALTER 문을 별도로 실행해야 한다.
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 아래 ALTER 문을 그대로 실행.

ALTER TABLE users
  ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user' AFTER provider_id;

-- 관리자 계정 지정 (수동, 별도 관리 UI 없음):
-- UPDATE users SET role = 'admin' WHERE id = <관리자로 지정할 user id>;
