-- 기본 챌린지 7종 시드 (#97 — UPSERT 방식으로 재실행해도 중복 생성되지 않음)
--
-- 전제: challenges.title에 UNIQUE 제약이 있어야 한다
--       (002_dedup_challenges_unique.sql 선행 적용 필요).
--
-- 실행: Cloudtype DB 콘솔(또는 mysql 클라이언트)에서 아래 문을 그대로 실행.
--       여러 번 실행해도 안전(ON DUPLICATE KEY UPDATE).

INSERT INTO challenges (title, description, target_type, target_value, is_ai_generated)
VALUES
  ('이번 주 배달 3회 이하', '배달을 조금만 줄여봐요. 3번은 OK!', 'delivery', 3, 0),
  ('이번 주 배달 2회 이하', '한 번만 더 줄여볼까요?', 'delivery', 2, 0),
  ('이번 주 배달 1회 이하', '거의 다 왔어요. 마지막 도전!', 'delivery', 1, 0),
  ('유튜브 주 5시간 이하', '유튜브 시간을 300분 이내로 줄여보세요.', 'time', 300, 0),
  ('SNS 하루 1시간 이하', '하루 60분, 생각보다 충분해요.', 'time', 420, 0),
  ('게임 주 10시간 이하', '게임 시간을 600분 이내로 줄여보세요.', 'time', 600, 0),
  ('배달+SNS 동시 줄이기', '배달 3회 이하 + SNS 3시간(180분) 이하 동시 달성!', 'both', 3, 0)
ON DUPLICATE KEY UPDATE
  description     = VALUES(description),
  target_type     = VALUES(target_type),
  target_value    = VALUES(target_value),
  is_ai_generated = VALUES(is_ai_generated);
