-- =============================================
-- XGuard Org Chart — Supabase Schema Setup
-- Run this in your Supabase SQL Editor
-- =============================================

-- 1. DEPARTMENTS
create table if not exists departments (
  id text primary key,
  label text not null,
  color text not null default '#60a5fa',
  sort_order int not null default 0,
  created_at timestamptz default now()
);

-- 2. PEOPLE
create table if not exists people (
  id text primary key,
  name text not null,
  role text,
  type text not null default 'contractor', -- 'vp' | 'lead' | 'employee' | 'contractor'
  dept text,                                -- references departments.id
  reports_to text,                          -- references people.id
  programs text[],                          -- array of program tags e.g. ['BSP','RCR']
  schedule text,
  delegate bool default false,
  notes text,
  avatar_color text default '#60a5fa',
  avatar_initials text,
  sort_order int default 0,
  created_at timestamptz default now()
);

-- 3. TASKS & OUTCOMES (per person)
create table if not exists tasks (
  id uuid primary key default gen_random_uuid(),
  person_id text not null references people(id) on delete cascade,
  tasks jsonb default '[]',
  outcomes text[],
  expected_outcomes text[],
  updated_at timestamptz default now()
);

-- 4. CANVAS ORDER (persists manual drag order in canvas view)
create table if not exists canvas_order (
  id text primary key,   -- parent id (e.g. 'vp', 'div_formation')
  children text[],       -- ordered list of child ids
  updated_at timestamptz default now()
);

-- Enable realtime on all tables
alter publication supabase_realtime add table departments;
alter publication supabase_realtime add table people;
alter publication supabase_realtime add table tasks;
alter publication supabase_realtime add table canvas_order;

-- Allow public read/write (no auth needed for internal tool)
alter table departments enable row level security;
alter table people enable row level security;
alter table tasks enable row level security;
alter table canvas_order enable row level security;

create policy "public all" on departments for all using (true) with check (true);
create policy "public all" on people for all using (true) with check (true);
create policy "public all" on tasks for all using (true) with check (true);
create policy "public all" on canvas_order for all using (true) with check (true);
