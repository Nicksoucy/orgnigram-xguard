-- ============================================================
-- XGuard Auth Setup — run this in Supabase SQL Editor
-- ============================================================

-- 1. Table user_profiles: links auth.users → instructor + role
--    NOTE: people.id is type TEXT, so instructor_id is also text (no foreign key)
create table if not exists public.user_profiles (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  instructor_id text,   -- matches people.id (text type, no FK constraint)
  role          text not null default 'formateur' check (role in ('admin','formateur')),
  created_at    timestamptz default now(),
  unique(user_id)
);

-- 2. Enable RLS
alter table public.user_profiles enable row level security;

-- Users can read their own profile
create policy "user_profiles: own read"
  on public.user_profiles for select
  using (auth.uid() = user_id);

-- Only admins can insert/update profiles (manage users)
create policy "user_profiles: admin write"
  on public.user_profiles for all
  using (
    exists (
      select 1 from public.user_profiles p
      where p.user_id = auth.uid() and p.role = 'admin'
    )
  );

-- 3. Schedule entries RLS (optional — uncomment if you want DB-level enforcement)
-- alter table public.schedule_entries enable row level security;
-- create policy "schedule_entries: admin all"
--   on public.schedule_entries for all
--   using (exists (select 1 from public.user_profiles p where p.user_id = auth.uid() and p.role = 'admin'));
-- create policy "schedule_entries: formateur own read"
--   on public.schedule_entries for select
--   using (instructor_id = (select instructor_id from public.user_profiles where user_id = auth.uid()));

-- ============================================================
-- 4. CREATE YOUR ADMIN ACCOUNT
--    Step 1: Go to Authentication → Users → "Invite user" → your email
--    Step 2: Find your UUID in that same Users list
--    Step 3: Run this (replace the UUID):
-- ============================================================
-- insert into public.user_profiles (user_id, role)
-- values ('YOUR-AUTH-USER-UUID-HERE', 'admin');


-- ============================================================
-- 5. CREATE A FORMATEUR ACCOUNT
--    Step 1: Invite the trainer in Authentication → Users
--    Step 2: Find their auth UUID + their people.id from the people table
--    Step 3: Run this:
-- ============================================================
-- insert into public.user_profiles (user_id, instructor_id, role)
-- values ('FORMATEUR-AUTH-UUID', 'THEIR-PEOPLE-ID-TEXT', 'formateur');


-- ============================================================
-- HELPER: find all people IDs to copy-paste above
-- ============================================================
-- select id, name from public.people order by name;
