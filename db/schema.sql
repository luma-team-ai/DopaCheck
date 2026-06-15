-- Dopamine Check DB 스키마 (PRD §11) — MariaDB 10.5+ / MySQL 8
--
-- 정책 (#21):
--   - users.id 는 BIGINT AUTO_INCREMENT 자체 PK. 소셜 로그인 시 (provider, provider_id) 로 upsert (#26).
--   - 나머지 테이블 id 는 uuid(CHAR(36)), user_id 는 BIGINT FK.
--   - 예외(#115): challenges.id / user_challenges.id 는 BIGINT AUTO_INCREMENT
--     (운영 DB 레거시 정수 PK + routes/challenge.py의 int(challenge_id) 전제와 일치).
--   - RLS 제거 — 모든 조회는 앱에서 WHERE user_id = session['user_id'] 로 스코프한다.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  id          BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email       VARCHAR(255) NOT NULL UNIQUE,    -- TODO(#26): 멀티프로바이더 동일 이메일 충돌 시 UNIQUE 제거 검토(DB담당 결정)
  nickname    VARCHAR(100),
  hourly_wage INT          NOT NULL DEFAULT 10030,
  -- 소셜로그인 식별키 (#26): upsert_user_profile 이 (provider, provider_id) 로 사용자 매칭
  provider    VARCHAR(20)  NOT NULL,           -- 'google' | 'kakao'
  provider_id VARCHAR(255) NOT NULL,           -- OAuth sub / 카카오 회원번호
  -- 관리자 페이지 접근 제어 (PRD Ver1.2 FR-52~54): 'user'(기본) | 'admin'.
  -- 'admin' 지정은 DB 직접 UPDATE로만 처리 (별도 관리 UI 없음).
  role        VARCHAR(20)  NOT NULL DEFAULT 'user',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_provider (provider, provider_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS delivery_records (
  id             CHAR(36) NOT NULL PRIMARY KEY DEFAULT (UUID()),
  user_id        BIGINT   NOT NULL,
  total_price    INT      NOT NULL,
  delivery_fee   INT      NOT NULL DEFAULT 0,
  total_calories INT,
  items          JSON,
  ai_comment     TEXT,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_delivery_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_delivery_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS time_records (
  id            CHAR(36) NOT NULL PRIMARY KEY DEFAULT (UUID()),
  user_id       BIGINT   NOT NULL,
  youtube_min   INT      NOT NULL DEFAULT 0,
  instagram_min INT      NOT NULL DEFAULT 0,
  tiktok_min    INT      NOT NULL DEFAULT 0,
  game_min      INT      NOT NULL DEFAULT 0,
  hourly_wage   INT      NOT NULL,
  ai_comment    TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_time_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_time_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dopamine_scores (
  id                    CHAR(36) NOT NULL PRIMARY KEY DEFAULT (UUID()),
  user_id               BIGINT   NOT NULL,
  score                 INT      NOT NULL CHECK (score BETWEEN 0 AND 100),
  delivery_contribution INT      NOT NULL DEFAULT 0,
  time_contribution     INT      NOT NULL DEFAULT 0,
  challenge_bonus       INT      NOT NULL DEFAULT 0,
  week_start            DATE     NOT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_score_user FOREIGN KEY (user_id) REFERENCES users(id),
  UNIQUE KEY uq_user_week (user_id, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS challenges (
  id              BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title           VARCHAR(255) NOT NULL,
  description     TEXT,
  target_type     VARCHAR(20)  NOT NULL CHECK (target_type IN ('delivery','time','both')),
  target_value    INT          NOT NULL,
  is_ai_generated TINYINT(1)   NOT NULL DEFAULT 0,
  CONSTRAINT uq_challenges_title UNIQUE (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_challenges (
  id           CHAR(36)   NOT NULL PRIMARY KEY DEFAULT (UUID()),
  user_id      BIGINT     NOT NULL,
  challenge_id BIGINT     NOT NULL,
  progress     INT        NOT NULL DEFAULT 0,
  is_completed TINYINT(1) NOT NULL DEFAULT 0,
  started_at   DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME   NULL,
  CONSTRAINT fk_uc_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_uc_challenge FOREIGN KEY (challenge_id) REFERENCES challenges(id),
  INDEX idx_uc_user_challenge (user_id, challenge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 활성(미완료) 동일 챌린지 중복 참여 차단(FR-35)은 MariaDB가 partial unique index를
-- 지원하지 않으므로 앱 레벨에서 처리한다(challenge join 시 미완료 동일 challenge_id 존재 검증).
-- idx_uc_user_challenge: SELECT … FOR UPDATE의 next-key lock이 올바른 범위에 걸리도록
-- (user_id, challenge_id) 복합 인덱스를 명시한다(풀 스캔 시 gap lock 미작동 위험 방어).

-- RLS 제거 — 모든 조회는 앱에서 WHERE user_id = session['user_id'] 로 스코프.
--   랭킹(FR-29, FR-30) 전체 집계는 서버에서 직접 집계 쿼리로 처리(별도 정책 불필요).

-- 기본 챌린지 7종 시드: db/seed.sql (UPSERT, #97)
