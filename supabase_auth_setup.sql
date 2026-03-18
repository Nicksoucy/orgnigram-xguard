-- ============================================================
-- XGuard Auth Setup — run this in Supabase SQL Editor
-- ============================================================

-- 1. Table user_profiles: links auth.users → instructor + role
create table if not exists public.user_profiles (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  instructor_id uuid references public.people(id) on delete set null,
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

-- 3. Schedule entries: formateurs can only see their own
--    (admins see everything — no restriction needed since anon key is used)
--    Uncomment and adapt if you want strict RLS on schedule_entries:
--
-- alter table public.schedule_entries enable row level security;
-- create policy "schedule_entries: admin all"
--   on public.schedule_entries for all
--   using (
--     exists (select 1 from public.user_profiles p where p.user_id = auth.uid() and p.role = 'admin')
--   );
-- create policy "schedule_entries: formateur own read"
--   on public.schedule_entries for select
--   using (
--     instructor_id = (select instructor_id from public.user_profiles where user_id = auth.uid())
--   );

-- 4. Create your first admin user profile (replace the UUID with your auth user id)
--    Find your user id in: Supabase Dashboard → Authentication → Users
--
-- insert into public.user_profiles (user_id, role)
-- values ('YOUR-AUTH-USER-UUID-HERE', 'admin');

-- 5. Create a formateur profile example:
--    After creating the user in Auth dashboard, link them to their instructor row:
--
-- insert into public.user_profiles (user_id, instructor_id, role)
-- values ('FORMATEUR-AUTH-UUID', 'THEIR-INSTRUCTOR-UUID-IN-PEOPLE-TABLE', 'formateur');
