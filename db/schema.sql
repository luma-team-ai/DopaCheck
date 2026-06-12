-- Dopamine Check DB 스키마 (PRD §11 — 담당: 김승현)
-- Supabase SQL Editor에서 실행

-- ── users ──────────────────────────────────────────────
create table if not exists users (
  id          uuid primary key references auth.users (id),
  email       text not null,
  nickname    text,
  hourly_wage integer not null default 10030,
  created_at  timestamptz not null default now()
);

-- ── delivery_records ───────────────────────────────────
create table if not exists delivery_records (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references users (id),
  total_price    integer not null,
  delivery_fee   integer not null default 0,
  total_calories integer,
  items          jsonb,          -- [{name, price, calories}]
  ai_comment     text,
  created_at     timestamptz not null default now()
);

-- ── time_records ───────────────────────────────────────
create table if not exists time_records (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users (id),
  youtube_min   integer not null default 0,
  instagram_min integer not null default 0,
  tiktok_min    integer not null default 0,
  game_min      integer not null default 0,
  hourly_wage   integer not null,
  ai_comment    text,
  created_at    timestamptz not null default now()
);

-- ── dopamine_scores ────────────────────────────────────
create table if not exists dopamine_scores (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references users (id),
  score                 integer not null check (score between 0 and 100),
  delivery_contribution integer not null default 0,
  time_contribution     integer not null default 0,
  challenge_bonus       integer not null default 0,
  week_start            date not null,   -- 해당 주 월요일
  created_at            timestamptz not null default now(),
  unique (user_id, week_start)           -- 주차별 1개 레코드 upsert (FR-31)
);

-- ── challenges ─────────────────────────────────────────
create table if not exists challenges (
  id              uuid primary key default gen_random_uuid(),
  title           text not null,
  description     text,
  target_type     text not null check (target_type in ('delivery', 'time', 'both')),
  target_value    integer not null,
  is_ai_generated boolean not null default false
);

-- ── user_challenges ────────────────────────────────────
create table if not exists user_challenges (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references users (id),
  challenge_id uuid not null references challenges (id),
  progress     integer not null default 0,
  is_completed boolean not null default false,
  started_at   timestamptz not null default now(),
  completed_at timestamptz
);

-- 활성(미완료) 상태 동일 챌린지 중복 참여 차단 (FR-35)
create unique index if not exists uq_active_user_challenge
  on user_challenges (user_id, challenge_id)
  where is_completed = false;

-- ── RLS 정책 (본인 데이터만 접근) ───────────────────────
alter table users             enable row level security;
alter table delivery_records  enable row level security;
alter table time_records      enable row level security;
alter table dopamine_scores   enable row level security;
alter table user_challenges   enable row level security;

create policy "본인 프로필만" on users
  for all using (auth.uid() = id);

create policy "본인 데이터만" on delivery_records
  for all using (auth.uid() = user_id);

create policy "본인 데이터만" on time_records
  for all using (auth.uid() = user_id);

create policy "본인 데이터만" on dopamine_scores
  for all using (auth.uid() = user_id);

create policy "본인 데이터만" on user_challenges
  for all using (auth.uid() = user_id);

-- challenges(공용 목록)는 로그인 사용자 모두 조회 가능
alter table challenges enable row level security;
create policy "로그인 사용자 조회" on challenges
  for select using (auth.role() = 'authenticated');

-- TODO(김승현): 랭킹(FR-29, FR-30)용 dopamine_scores 집계 정책 검토
--   (전체 평균·상위 N%는 RLS 우회 필요 → service key 사용 또는 view/rpc로 해결)
-- TODO(김승현): 시드 더미 데이터 20건 삽입 스크립트 작성 (db/seed.sql)
