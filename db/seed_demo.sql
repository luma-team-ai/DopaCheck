-- 랭킹/percentile 시연용 더미 데이터 20건 (#131) — ⚠️ 시연 전용, 운영 DB 실행 금지
--
-- admin 랭킹·점수 분포 화면(FR-29·FR-30)을 채우기 위한 가짜 사용자 20명 + 이번 주 점수.
-- 특징:
--   - 재실행 안전(idempotent): users=(provider,provider_id) UNIQUE, scores=(user_id,week_start) UNIQUE,
--     records=고정 UUID PK → 전부 ON DUPLICATE KEY UPDATE.
--   - week_start는 CURDATE() 기준 이번 주 월요일로 자동 계산(WEEKDAY: 월=0) → 언제 실행해도 '이번 주'로 노출.
--   - 모든 계정은 provider='seed' 로 표식 → 정리 시 `DELETE FROM users WHERE provider='seed'` (FK 자식 먼저 삭제).
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 그대로 실행.
SET NAMES utf8mb4;
SET @wk := DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY);  -- 이번 주 월요일

-- 1) 더미 사용자 20명
INSERT INTO users (email, nickname, hourly_wage, provider, provider_id, role) VALUES
  ('demo01@dopacheck.example', '데모유저01', 10030, 'seed', 'seed-01', 'user'),
  ('demo02@dopacheck.example', '데모유저02', 10030, 'seed', 'seed-02', 'user'),
  ('demo03@dopacheck.example', '데모유저03', 10030, 'seed', 'seed-03', 'user'),
  ('demo04@dopacheck.example', '데모유저04', 10030, 'seed', 'seed-04', 'user'),
  ('demo05@dopacheck.example', '데모유저05', 10030, 'seed', 'seed-05', 'user'),
  ('demo06@dopacheck.example', '데모유저06', 10030, 'seed', 'seed-06', 'user'),
  ('demo07@dopacheck.example', '데모유저07', 10030, 'seed', 'seed-07', 'user'),
  ('demo08@dopacheck.example', '데모유저08', 10030, 'seed', 'seed-08', 'user'),
  ('demo09@dopacheck.example', '데모유저09', 10030, 'seed', 'seed-09', 'user'),
  ('demo10@dopacheck.example', '데모유저10', 10030, 'seed', 'seed-10', 'user'),
  ('demo11@dopacheck.example', '데모유저11', 10030, 'seed', 'seed-11', 'user'),
  ('demo12@dopacheck.example', '데모유저12', 10030, 'seed', 'seed-12', 'user'),
  ('demo13@dopacheck.example', '데모유저13', 10030, 'seed', 'seed-13', 'user'),
  ('demo14@dopacheck.example', '데모유저14', 10030, 'seed', 'seed-14', 'user'),
  ('demo15@dopacheck.example', '데모유저15', 10030, 'seed', 'seed-15', 'user'),
  ('demo16@dopacheck.example', '데모유저16', 10030, 'seed', 'seed-16', 'user'),
  ('demo17@dopacheck.example', '데모유저17', 10030, 'seed', 'seed-17', 'user'),
  ('demo18@dopacheck.example', '데모유저18', 10030, 'seed', 'seed-18', 'user'),
  ('demo19@dopacheck.example', '데모유저19', 10030, 'seed', 'seed-19', 'user'),
  ('demo20@dopacheck.example', '데모유저20', 10030, 'seed', 'seed-20', 'user')
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), hourly_wage=VALUES(hourly_wage), role=VALUES(role);

-- 2) 이번 주 도파민 점수 (percentile 분포용, 8~93)
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000001', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-01') AS u), 8, 4, 3, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000002', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-02') AS u), 12, 6, 5, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000003', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-03') AS u), 17, 8, 7, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000004', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-04') AS u), 21, 10, 8, -5, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000005', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-05') AS u), 26, 13, 10, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000006', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-06') AS u), 30, 15, 12, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000007', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-07') AS u), 35, 18, 14, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000008', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-08') AS u), 39, 20, 16, -5, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000009', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-09') AS u), 44, 22, 18, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000010', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-10') AS u), 48, 24, 19, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000011', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-11') AS u), 53, 26, 21, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000012', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-12') AS u), 57, 28, 23, -5, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000013', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-13') AS u), 62, 31, 25, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000014', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-14') AS u), 66, 33, 26, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000015', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-15') AS u), 71, 36, 28, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000016', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-16') AS u), 75, 38, 30, -5, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000017', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-17') AS u), 80, 40, 32, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000018', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-18') AS u), 84, 42, 34, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000019', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-19') AS u), 89, 44, 36, 0, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);
INSERT INTO dopamine_scores (id, user_id, score, delivery_contribution, time_contribution, challenge_bonus, week_start) VALUES ('11111111-0000-4000-8000-000000000020', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-20') AS u), 93, 46, 37, -5, @wk)
ON DUPLICATE KEY UPDATE score=VALUES(score), delivery_contribution=VALUES(delivery_contribution), time_contribution=VALUES(time_contribution), challenge_bonus=VALUES(challenge_bonus);

-- 3) 이번 주 배달 기록 (1인 1건)
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000001', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-01') AS u), 12900, 3000, 755, JSON_ARRAY(JSON_OBJECT('name','치킨','price',9900)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000002', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-02') AS u), 13800, 3000, 810, JSON_ARRAY(JSON_OBJECT('name','치킨','price',10800)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000003', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-03') AS u), 14700, 3000, 865, JSON_ARRAY(JSON_OBJECT('name','치킨','price',11700)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000004', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-04') AS u), 15600, 3000, 920, JSON_ARRAY(JSON_OBJECT('name','치킨','price',12600)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000005', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-05') AS u), 16500, 3000, 975, JSON_ARRAY(JSON_OBJECT('name','치킨','price',13500)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000006', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-06') AS u), 17400, 3000, 1030, JSON_ARRAY(JSON_OBJECT('name','치킨','price',14400)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000007', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-07') AS u), 18300, 3000, 1085, JSON_ARRAY(JSON_OBJECT('name','치킨','price',15300)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000008', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-08') AS u), 19200, 3000, 1140, JSON_ARRAY(JSON_OBJECT('name','치킨','price',16200)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000009', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-09') AS u), 20100, 3000, 1195, JSON_ARRAY(JSON_OBJECT('name','치킨','price',17100)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000010', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-10') AS u), 21000, 3000, 1250, JSON_ARRAY(JSON_OBJECT('name','치킨','price',18000)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000011', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-11') AS u), 21900, 3000, 1305, JSON_ARRAY(JSON_OBJECT('name','치킨','price',18900)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000012', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-12') AS u), 22800, 3000, 1360, JSON_ARRAY(JSON_OBJECT('name','치킨','price',19800)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000013', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-13') AS u), 23700, 3000, 1415, JSON_ARRAY(JSON_OBJECT('name','치킨','price',20700)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000014', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-14') AS u), 24600, 3000, 1470, JSON_ARRAY(JSON_OBJECT('name','치킨','price',21600)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000015', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-15') AS u), 25500, 3000, 1525, JSON_ARRAY(JSON_OBJECT('name','치킨','price',22500)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000016', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-16') AS u), 26400, 3000, 1580, JSON_ARRAY(JSON_OBJECT('name','치킨','price',23400)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000017', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-17') AS u), 27300, 3000, 1635, JSON_ARRAY(JSON_OBJECT('name','치킨','price',24300)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000018', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-18') AS u), 28200, 3000, 1690, JSON_ARRAY(JSON_OBJECT('name','치킨','price',25200)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000019', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-19') AS u), 29100, 3000, 1745, JSON_ARRAY(JSON_OBJECT('name','치킨','price',26100)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);
INSERT INTO delivery_records (id, user_id, total_price, delivery_fee, total_calories, items, ai_comment, created_at) VALUES ('22222222-0000-4000-8000-000000000020', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-20') AS u), 30000, 3000, 1800, JSON_ARRAY(JSON_OBJECT('name','치킨','price',27000)), '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE total_price=VALUES(total_price), total_calories=VALUES(total_calories);

-- 4) 이번 주 시간 기록 (1인 1건)
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000001', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-01') AS u), 40, 28, 16, 22, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000002', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-02') AS u), 50, 36, 22, 29, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000003', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-03') AS u), 60, 44, 28, 36, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000004', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-04') AS u), 70, 52, 34, 43, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000005', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-05') AS u), 80, 60, 40, 50, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000006', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-06') AS u), 90, 68, 46, 57, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000007', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-07') AS u), 100, 76, 52, 64, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000008', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-08') AS u), 110, 84, 58, 71, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000009', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-09') AS u), 120, 92, 64, 78, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000010', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-10') AS u), 130, 100, 70, 85, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000011', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-11') AS u), 140, 108, 76, 92, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000012', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-12') AS u), 150, 116, 82, 99, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000013', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-13') AS u), 160, 124, 88, 106, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000014', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-14') AS u), 170, 132, 94, 113, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000015', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-15') AS u), 180, 140, 100, 120, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000016', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-16') AS u), 190, 148, 106, 127, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000017', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-17') AS u), 200, 156, 112, 134, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000018', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-18') AS u), 210, 164, 118, 141, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000019', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-19') AS u), 220, 172, 124, 148, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);
INSERT INTO time_records (id, user_id, youtube_min, instagram_min, tiktok_min, game_min, hourly_wage, ai_comment, created_at) VALUES ('33333333-0000-4000-8000-000000000020', (SELECT id FROM (SELECT id FROM users WHERE provider='seed' AND provider_id='seed-20') AS u), 230, 180, 130, 155, 10030, '시연용 더미 기록', @wk)
ON DUPLICATE KEY UPDATE youtube_min=VALUES(youtube_min), instagram_min=VALUES(instagram_min), tiktok_min=VALUES(tiktok_min), game_min=VALUES(game_min);

-- 정리(시연 후): 자식 테이블 먼저 → users 순으로 삭제
--   DELETE tr FROM time_records tr JOIN users u ON tr.user_id=u.id WHERE u.provider='seed';
--   DELETE dr FROM delivery_records dr JOIN users u ON dr.user_id=u.id WHERE u.provider='seed';
--   DELETE ds FROM dopamine_scores ds JOIN users u ON ds.user_id=u.id WHERE u.provider='seed';
--   DELETE FROM users WHERE provider='seed';
