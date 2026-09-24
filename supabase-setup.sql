-- San Dimas Canyon golf: leaderboard table.
-- Paste this whole file into Supabase: SQL Editor -> New query -> Run.
-- Anyone with the game link can add a score and read the leaderboard. Nobody can edit or delete a score
-- (there are no update or delete rules), and the checks below turn away junk entries.

create table if not exists public.scores (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  player      text not null check (char_length(btrim(player)) between 1 and 20),
  mode        text not null check (mode in ('daily', 'round')),
  day         date not null check (day between current_date - 2 and current_date + 2),
  tees        text not null check (tees in ('blue', 'white', 'red')),
  level       text not null check (level in ('tour', 'scratch', 'hcp10', 'hcp20')),
  strokes     int  not null check (strokes between 1 and 200),
  par         int  not null check (par between 3 and 72),
  holes       int[] not null check (array_length(holes, 1) between 1 and 18),
  client_id   uuid not null
);

-- One scored daily challenge per device per day
create unique index if not exists scores_one_daily_per_device
  on public.scores (day, client_id) where mode = 'daily';

create index if not exists scores_board on public.scores (mode, day, strokes);

alter table public.scores enable row level security;

drop policy if exists "anyone can read scores" on public.scores;
create policy "anyone can read scores" on public.scores
  for select to anon, authenticated using (true);

drop policy if exists "anyone can add a score" on public.scores;
create policy "anyone can add a score" on public.scores
  for insert to anon, authenticated with check (true);

-- The client_id is only used to stop repeat daily entries; players never see each other's.
-- Supabase grants everything on new tables by default, so take that back and grant column by column.
revoke all on public.scores from anon, authenticated;
grant select (id, created_at, player, mode, day, tees, level, strokes, par, holes) on public.scores to anon, authenticated;
grant insert (player, mode, day, tees, level, strokes, par, holes, client_id) on public.scores to anon, authenticated;
